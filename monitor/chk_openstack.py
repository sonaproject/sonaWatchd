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


def get_gw_ratio(conn, node_name, node_ip, cur_val, total_val):
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
        packet_cnt = 0
        for nodename, nodelist, ip in nodes_info:
            if not nodelist == 'none':
                for line in str(nodelist).splitlines():
                    if 'managementIp=' + node_ip + ',' in line:
                        tmp = line.split(',')

                        for col in tmp:
                            if 'managementIp' in col:
                                data_ip = col.split('=')[1]
                                manage_ip = ip
                                break

                    if not manage_ip == '':
                        break
            if not manage_ip == '':
                break

        if data_ip == '':
            LOG.info('Can not find data ip')
            return 'fail'

        group_rt = SshCommand.onos_ssh_exec(manage_ip, 'groups')

        if group_rt is not None:
            for line in group_rt.splitlines():
                if '{tunnelDst=' + data_ip + '}' in line:
                    tmp = line.split(',')

                    for col in tmp:
                        if 'packets=' in col:
                            packet_cnt = packet_cnt + int(col.split('=')[1])

        if cur_val == -1 or total_val == 0:
            LOG.info('GW Ratio Fail.')
            strRatio = 'fail'
            ratio = 0
        else:
            if cur_val == 0:
                ratio = 0
            else:
                ratio = float(cur_val) * 100 / total_val

            strRatio = 'Received packet count = ' + str(cur_val) + '\n'
            strRatio = strRatio + 'compute nodes -> ' + node_name + ' Packet count = ' + str(packet_cnt) + '\n'
            strRatio = strRatio + str(ratio) + ' (' + str(cur_val) + ' / ' + str(total_val) + ')'

            if cur_val < packet_cnt:
                LOG.info('GW Ratio Fail. (Data loss)')
                strRatio = strRatio + '(packet loss)'
            else:
                strRatio = strRatio + '(no packet loss)'

        try:
            sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
                  ' SET gw_ratio = \'' + strRatio + '\'' + \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update GW Ratio info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('OPENSTACK(gw_ratio) DB Update Fail.')
        except:
            LOG.exception()

        LOG.info('GW Ratio = ' + str(ratio))
        if ratio < float(CONF.alarm()['gw_ratio']) or cur_val < packet_cnt:
            return 'nok'

        return 'ok'
    except:
        LOG.exception()
        return 'fail'


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


def calc_node_traffic_ratio(total_rx, total_tx):
    try:
        if total_rx == 0 and total_tx == 0:
            ratio = 100
        elif total_tx == 0:
            LOG.info('Node Traffic Ratio Fail.')
            ratio = 0
        else:
            ratio = float(total_rx) * 100 / total_tx

        LOG.info('Node Traffic Ratio = ' + str(ratio))
        return ratio
    except:
        LOG.exception()
        return -1


def get_node_traffic(conn, node_name, ratio, rx_dic, tx_dic, rx_total, tx_total, err_info):
    try:
        strRatio = '(VXLAN) Received packet count = ' + str(rx_dic[node_name]) + ', drop = ' + str(err_info['rx_drop']) + ', errs = ' + str(err_info['rx_err']) + '\n'
        strRatio = strRatio + '(VXLAN) Sent packet count = ' + str(tx_dic[node_name]) + ', drop = ' + str(err_info['tx_drop']) + ', errs = ' + str(err_info['tx_err']) + '\n'
        strRatio = strRatio + 'Ratio of success for all nodes = ' + str(ratio)  + ' (' + str(rx_total) + ' / ' + str(tx_total) + ')'

        try:
            sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
                  ' SET vxlan_traffic = \'' + strRatio + '\'' + \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update Node Traffic Ratio info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('DB Update Fail.')
        except:
            LOG.exception()

        LOG.info('Node Traffic Ratio = ' + str(ratio))
        if ratio < float(CONF.alarm()['node_traffic_ratio']):
            LOG.info('[NODE TRAFFIC] ratio nok')
            return 'nok'
        elif err_info['rx_drop'] > 0:
            LOG.info('[NODE TRAFFIC] rx_drop nok')
            return 'nok'
        elif err_info['rx_err'] > 0:
            LOG.info('[NODE TRAFFIC] rx_err nok')
            return 'nok'
        elif err_info['tx_drop'] > 0:
            LOG.info('[NODE TRAFFIC] tx_drop nok')
            return 'nok'
        elif err_info['tx_err'] > 0:
            LOG.info('[NODE TRAFFIC] tx_err nok')
            return 'nok'

        return 'ok'
    except:
        LOG.exception()
        return 'fail'


def get_internal_traffic(conn, node_name, node_ip, user_name, sub_type, rx_count, patch_tx):
    try:
        status = 'ok'

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
            else:
                status = 'fail'
                strmsg = 'fail'
        else:
            strmsg = 'vxlan rx = ' + str(rx_count) + ', patch-integ tx = ' + str(patch_tx)

            if patch_tx == -1:
                status = 'nok'
            else:
                in_packet = rx_count
                out_packet = patch_tx


        if status == 'ok':
            if in_packet == 0 and out_packet == 0:
                ratio = 100
            elif in_packet == 0:
                LOG.info('Internal Traffic Ratio Fail.')
                ratio = 0
            else:
                ratio = float(out_packet) * 100 / in_packet

            LOG.info('Internal Traffic Ratio = ' + str(ratio))

            if ratio < float(CONF.alarm()['internal_traffic_ratio']):
                status = 'nok'

        if sub_type == 'COMPUTE':
            if status == 'ok':
                op = '='
            else:
                op = '!='

            strmsg = 'in_port(' + str(inport_cnt) + ') + vxlan_rx(' + str(rx_count) + ') ' + op + ' gw(' + str(
                gw_cnt) + ') + output(' + str(output_cnt) + ')'

        try:
            sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
                  ' SET internal_traffic = \'' + strmsg + '\'' + \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update Internal Traffic info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('OPENSTACK(internal_traffic) DB Update Fail.')
        except:
            LOG.exception()

        return status
    except:
        LOG.exception()
        return 'fail'


