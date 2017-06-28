import cmd_proc
from api.sona_log import LOG
from api.config import CONF
from api.watcherdb import DB
from api.sbapi import SshCommand


def vrouter_check(conn, node_name, user_name, node_ip):
    str_docker = ''
    onos_id = ''

    ret_docker = 'ok'

    docker_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo docker ps')

    if docker_rt is not None:
        quagga_count = 0
        onos_count = 0

        try:
            for line in docker_rt.splitlines():
                str_docker = str_docker + line + '\n'

                if line.startswith('CONTAINER'):
                    continue

                tmp_line = line.split()

                if 'quagga' in tmp_line[1]:
                    quagga_count = quagga_count + 1

                    if not 'Up' in line:
                        ret_docker = 'nok'

                elif 'onos' in tmp_line[1]:
                    onos_count = onos_count + 1
                    onos_id = tmp_line[0]

                    if not 'Up' in line:
                        ret_docker = 'nok'

            if not (quagga_count == 2 and onos_count == 1):
                ret_docker = 'nok'
        except:
            LOG.exception()
    else:
        LOG.error("\'%s\' Vrouter Node Check Error", node_ip)
        str_docker = 'fail'

    str_onosapp = 'fail'
    str_route = 'fail'

    if onos_count == 1:
        # get onos container ip
        onos_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo docker inspect ' + onos_id + ' | grep IPAddress')

        if onos_rt is not None:
            for line in onos_rt.splitlines():
                line = line.strip()
                if line.startswith('\"IPAddress'):
                    tmp = line.split(':')
                    onos_ip = tmp[1].strip().replace('\"', '').replace(',', '')
                    break

            str_onosapp = SshCommand.ssh_pexpect(user_name, node_ip, onos_ip, 'apps -a -s')
            str_route = SshCommand.ssh_pexpect(user_name, node_ip, onos_ip, 'routes')

    try:
        sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
              ' SET docker = \'' + str_docker + '\',' + \
              ' onosApp = \'' + str_onosapp + '\',' + \
              ' routingTable = \'' + str_route + '\'' + \
              ' WHERE nodename = \'' + node_name + '\''
        LOG.info('Update Vrouter info = ' + sql)

        if DB.sql_execute(sql, conn) != 'SUCCESS':
            LOG.error('OPENSTACK(gateway) DB Update Fail.')
    except:
        LOG.exception()

    return ret_docker


def get_gw_ratio(conn, node_name, node_ip, rx, gw_rx_sum, pre_stat):
    status = 'ok'

    try:
        sql = 'SELECT ' + DB.ONOS_TBL + '.nodename, nodelist, ip_addr' + ' FROM ' + DB.ONOS_TBL + \
                ' INNER JOIN ' + DB.NODE_INFO_TBL + ' ON ' + DB.ONOS_TBL + '.nodename = ' + DB.NODE_INFO_TBL + '.nodename'

        nodes_info = conn.cursor().execute(sql).fetchall()

        if len(nodes_info) == 0:
            LOG.info('Fail to load onos list')
            return 'fail'

        # search data_ip
        data_ip = ''
        manage_ip = ''
        cpt_to_gw_packet = 0
        for nodename, nodelist, ip in nodes_info:
            if not nodelist == 'none':
                for line in str(nodelist).splitlines():
                    if (not (line.startswith('Total') or line.startswith('Hostname'))) and node_ip in line:
                        new_line = " ".join(line.split())

                        tmp = new_line.split(' ')
                        if tmp[3].startswith('of:'):
                            data_ip = tmp[4]
                        else:
                            data_ip = tmp[3]
                        manage_ip = node_ip

                    if not manage_ip == '':
                        break
            if not manage_ip == '':
                break

        if data_ip == '':
            LOG.info('Can not find data ip')
            return 'fail', pre_stat

        group_rt = SshCommand.onos_ssh_exec(manage_ip, 'groups')

        if group_rt is not None:
            for line in group_rt.splitlines():
                if '{tunnelDst=' + data_ip + '}' in line:
                    tmp = line.split(',')

                    for col in tmp:
                        if 'packets=' in col:
                            cpt_to_gw_packet = cpt_to_gw_packet + int(col.split('=')[1])

        if rx == -1 or gw_rx_sum == 0:
            LOG.info('GW Ratio Fail.')
            strRatio = 'fail'
        else:
            strRatio = 'Received packet count = ' + str(rx) + '\n'
            strRatio = strRatio + 'compute nodes -> ' + node_name + ' Packet count = ' + str(cpt_to_gw_packet) + '\n'

            if not dict(pre_stat).has_key(node_name + '_GW'):
                status = '-'
            else:
                cur_rx = rx - int(dict(pre_stat)[node_name + '_GW']['rx'])
                cur_total = gw_rx_sum - int(dict(pre_stat)[node_name + '_GW']['gw_rx_sum'])
                cur_packet = cpt_to_gw_packet - int(dict(pre_stat)[node_name + '_GW']['cpt_to_gw_packet'])

                if cur_rx == 0:
                    ratio = 0
                else:
                    ratio = float(cur_rx) * 100 / cur_total

                strRatio = strRatio + '[LAST ' + str(CONF.watchdog()['interval']) + ' Sec] GW RATIO = ' + str(ratio) + ' (' + str(cur_rx) + ' / ' + str(cur_total) + ')'

                if cur_rx < cur_packet:
                    LOG.info('GW Ratio Fail. (Data loss)')
                    strRatio = strRatio + '(packet loss)'
                else:
                    strRatio = strRatio + '(no packet loss)'

                LOG.info('GW Ratio = ' + str(ratio))

                if ratio < float(CONF.alarm()['gw_ratio']) or cur_rx < cur_packet:
                    status = 'nok'

        try:
            sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
                  ' SET gw_ratio = \'' + strRatio + '\'' + \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update GW Ratio info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('OPENSTACK(gw_ratio) DB Update Fail.')
        except:
            LOG.exception()

        in_out_dic = dict()
        in_out_dic['rx'] = rx
        in_out_dic['gw_rx_sum'] = gw_rx_sum
        in_out_dic['cpt_to_gw_packet'] = cpt_to_gw_packet

        pre_stat[node_name + '_GW'] = in_out_dic
    except:
        LOG.exception()
        status = 'fail'

    return status, pre_stat


def rx_tx_check(user_name, node_ip):
    try:
        port_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo ovs-ofctl show br-int')

        err_dict = dict()
        patch_port = None
        if port_rt is not None:
            for line in port_rt.splitlines():
                if '(vxlan)' in line:
                    vxlan_port = line.split('(')[0].strip()
                elif '(patch-intg)' in line:
                    patch_port = line.split('(')[0].strip()

            port_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo ovs-ofctl dump-ports br-int ' + vxlan_port)

            if port_rt is not None:
                line = port_rt.splitlines()

                if '?' in line[1]:
                    line[1] = line[1].replace('?', '0')

                if '?' in line[2]:
                    line[2] = line[2].replace('?', '0')

                tmp = line[1].split(',')
                rx_packet_cnt = int(tmp[0].split('=')[1])
                err_dict['rx_drop'] = int(tmp[2].split('=')[1])
                err_dict['rx_err'] = int(tmp[3].split('=')[1])

                tmp = line[2].split(',')
                tx_packet_cnt = int(tmp[0].split('=')[1])
                err_dict['tx_drop'] = int(tmp[2].split('=')[1])
                err_dict['tx_err'] = int(tmp[3].split('=')[1])
            else:
                rx_packet_cnt = -1
                tx_packet_cnt = -1

            patch_tx_packet_cnt = -1

            # find patch port
            if not patch_port is None:
                port_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo ovs-ofctl dump-ports br-int ' + patch_port)

                if port_rt is not None:
                    line = port_rt.splitlines()

                    if '?' in line[2]:
                        line[2] = line[2].replace('?', '0')

                    tmp = line[2].split(',')
                    patch_tx_packet_cnt = int(tmp[0].split('=')[1])

            return rx_packet_cnt, tx_packet_cnt, err_dict, patch_tx_packet_cnt
    except:
        LOG.exception()

    return -1, -1, err_dict, -1


def get_node_traffic(conn, node_name, rx_dic, tx_dic, total_rx, total_tx, err_info, pre_stat):
    try:
        status = 'ok'

        pre_total_rx = total_rx
        pre_total_tx = total_tx

        if not dict(pre_stat).has_key('VXLAN'):
            status = '-'
            ratio = -1
        else:
            total_rx = total_rx - int(dict(pre_stat)['VXLAN']['total_rx'])
            total_tx = total_tx - int(dict(pre_stat)['VXLAN']['total_tx'])

            if total_rx == 0 and total_tx == 0:
                ratio = 100
            elif total_tx <= 0 or total_tx < 0:
                LOG.info('Node Traffic Ratio Fail.')
                ratio = 0
            else:
                ratio = float(total_rx) * 100 / total_tx

        LOG.info('Node Traffic Ratio = ' + str(ratio))

        strRatio = 'rx = ' + str(rx_dic[node_name]) + ', drop = ' + str(err_info['rx_drop']) + ', errs = ' + str(err_info['rx_err']) + '\n'
        strRatio = strRatio + 'tx = ' + str(tx_dic[node_name]) + ', drop = ' + str(err_info['tx_drop']) + ', errs = ' + str(err_info['tx_err']) + '\n'

        if not status == '-':
            strRatio = strRatio + '* [LAST ' + str(CONF.watchdog()['interval']) + ' Sec] Ratio of success for all nodes = ' + str(ratio)  + ' (' + str(total_rx) + ' / ' + str(total_tx) + ')'

            if ratio < float(CONF.alarm()['node_traffic_ratio']):
                LOG.info('[NODE TRAFFIC] ratio nok')
                status = 'nok'

            if err_info['rx_drop'] - int(dict(pre_stat)['VXLAN']['rx_drop']) > 0:
                LOG.info('[NODE TRAFFIC] rx_drop nok')
                status = 'nok'

            if err_info['rx_err'] - int(dict(pre_stat)['VXLAN']['rx_err']) > 0:
                LOG.info('[NODE TRAFFIC] rx_err nok')
                status = 'nok'

            if err_info['tx_drop'] - int(dict(pre_stat)['VXLAN']['tx_drop']) > 0:
                LOG.info('[NODE TRAFFIC] tx_drop nok')
                status = 'nok'

            if err_info['tx_err'] - int(dict(pre_stat)['VXLAN']['tx_err']) > 0:
                LOG.info('[NODE TRAFFIC] tx_err nok')
                status = 'nok'

        try:
            sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
                  ' SET vxlan_traffic = \'' + strRatio + '\'' + \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update Node Traffic Ratio info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('DB Update Fail.')
        except:
            LOG.exception()

        in_out_dic = dict()
        in_out_dic['total_rx'] = pre_total_rx
        in_out_dic['total_tx'] = pre_total_tx

        in_out_dic['rx_drop'] = err_info['rx_drop']
        in_out_dic['rx_err'] = err_info['rx_err']
        in_out_dic['tx_drop'] = err_info['tx_drop']
        in_out_dic['tx_err'] = err_info['tx_err']

        pre_stat['VXLAN'] = in_out_dic

        return status, pre_stat
    except:
        LOG.exception()
        return 'fail', pre_stat


def get_internal_traffic(conn, node_name, node_ip, user_name, sub_type, rx_count, patch_tx, pre_stat):
    try:
        status = 'ok'
        in_packet = 0
        out_packet = 0

        if sub_type == 'COMPUTE':
            flow_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo ovs-ofctl -O OpenFlow13 dump-flows br-int')

            inport_cnt = 0
            gw_cnt = 0
            output_cnt = 0

            if flow_rt is not None:
                for line in flow_rt.splitlines():
                    tmp = line.split(',')
                    if 'in_port' in line:
                        inport_cnt = inport_cnt + int(tmp[3].split('=')[1])
                    elif 'output' in line:
                        output_cnt = output_cnt + int(tmp[3].split('=')[1])
                    elif 'actions=group' in line:
                        gw_cnt = gw_cnt + int(tmp[3].split('=')[1])

                in_packet = inport_cnt + rx_count
                out_packet = gw_cnt + output_cnt

                strmsg = 'IN[vm_tx = ' + str(inport_cnt) + ', vxlan_rx = ' + str(rx_count) + '], OUT[gw = ' + str(gw_cnt) + ', output = ' + str(output_cnt) + ']'
            else:
                status = 'fail'
                strmsg = 'fail'

        else:
            strmsg = 'IN[vxlan rx = ' + str(rx_count) + '], OUT[patch-integ tx = ' + str(patch_tx) + ']'

            if patch_tx == -1:
                status = 'nok'
            else:
                in_packet = rx_count
                out_packet = patch_tx

        for_save_in = in_packet
        for_save_out = out_packet

        if not dict(pre_stat).has_key(node_name + '_internal'):
            status = '-'
        elif status == 'ok':
            in_packet = in_packet - int(dict(pre_stat)[node_name + '_internal']['in_packet'])
            out_packet = out_packet - int(dict(pre_stat)[node_name + '_internal']['out_packet'])

            if in_packet == 0 and out_packet == 0:
                ratio = 100
            elif in_packet <= 0 or out_packet < 0:
                LOG.info('Internal Traffic Ratio Fail.')
                ratio = 0
            else:
                ratio = float(out_packet) * 100 / in_packet

            LOG.info('Internal Traffic Ratio = ' + str(ratio))
            strmsg = strmsg + '\n* [LAST ' + str(CONF.watchdog()['interval']) + ' Sec] Internal Traffic Ratio = ' + str(ratio) + '(' + str(out_packet) + '/' + str(in_packet) + ')\n'

            if ratio < float(CONF.alarm()['internal_traffic_ratio']):
                status = 'nok'

        in_out_dic = dict()
        in_out_dic['in_packet'] = for_save_in
        in_out_dic['out_packet'] = for_save_out
        pre_stat[node_name + '_internal'] = in_out_dic

        try:
            sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
                  ' SET internal_traffic = \'' + strmsg + '\'' + \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update Internal Traffic info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('OPENSTACK(internal_traffic) DB Update Fail.')
        except:
            LOG.exception()

        return status, pre_stat
    except:
        LOG.exception()
        return 'fail', pre_stat


