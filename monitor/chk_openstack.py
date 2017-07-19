from api.sona_log import LOG
from api.config import CONF
from api.watcherdb import DB
from api.sbapi import SshCommand


def vrouter_check(conn, db_log, node_name, user_name, node_ip):
    ret_docker = 'ok'

    docker_list = []
    fail_list = []

    onos_id = ''

    docker_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo docker ps')

    if docker_rt is not None:
        try:
            for docker in CONF.openstack()['docker_list']:
                for line in docker_rt.splitlines():
                    if line.startswith('CONTAINER'):
                        continue

                    tmp_line = line.split()

                    if ' ' + docker in line:
                         if not 'Up' in line:
                             docker_json = {'name': docker, 'status': 'nok', 'type': 'docker'}
                             fail_list.append(docker_json)
                             ret_docker = 'nok'
                         else:
                             docker_json = {'name': docker, 'status': 'ok', 'type': 'docker'}

                         docker_list.append(docker_json)

                    if 'onos' in tmp_line[1]:
                        onos_id = tmp_line[0]
        except:
            LOG.exception()
    else:
        LOG.error("\'%s\' Vrouter Node Check Error", node_ip)
        ret_docker = 'fail'

    onos_app_list = []
    route_list = []

    if not onos_id == '':
        try:
            # get onos container ip
            onos_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo docker inspect ' + onos_id + ' | grep IPAddress')

            if onos_rt is not None:
                for line in onos_rt.splitlines():
                    line = line.strip()
                    if line.startswith('\"IPAddress'):
                        tmp = line.split(':')
                        onos_ip = tmp[1].strip().replace('\"', '').replace(',', '')
                        break

                app_list = SshCommand.ssh_pexpect(user_name, node_ip, onos_ip, 'apps -a -s')

                app_active_list = list()
                for line in app_list.splitlines():
                    app_active_list.append(line.split(".")[2].split()[0])

                for app in CONF.openstack()['onos_vrouter_app_list']:
                    if app in app_active_list:
                        app_json = {'name': app, 'status': 'ok', 'type': 'onos_app'}
                    else:
                        app_json = {'name': app, 'status': 'nok', 'type': 'onos_app'}
                        fail_list.append(app_json)
                        ret_docker = 'nok'

                    onos_app_list.append(app_json)

                str_route = SshCommand.ssh_pexpect(user_name, node_ip, onos_ip, 'routes')

                for line in str_route.splitlines():
                    line = line.strip()

                    if (line.startswith('Table') or line.startswith('Network') or line.startswith('Total')):
                        continue

                    new_line = " ".join(line.split())
                    tmp = new_line.split(' ')
                    route_json = {'network': tmp[0], 'next_hop': tmp[1]}
                    route_list.append(route_json)
        except:
            LOG.exception()
    else:
        LOG.info('can not find onos_id.')
        ret_docker = 'fail'

    try:
        sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
              ' SET docker = \"' + str(docker_list) + '\",' + \
              ' onosApp = \"' + str(onos_app_list) + '\",' + \
              ' routingTable = \"' + str(route_list) + '\"' + \
              ' WHERE nodename = \'' + node_name + '\''
        db_log.write_log('----- UPDATE GATEWAY INFO -----\n' + sql)

        if DB.sql_execute(sql, conn) != 'SUCCESS':
            db_log.write_log('[FAIL] GATEWAY DB Update Fail.')
    except:
        LOG.exception()

    return ret_docker, str(fail_list)


def get_gw_ratio_gateway(conn, db_log, node_ip, node_name, rx, gw_rx_sum, pre_stat):
    status = 'ok'
    reason = ''

    try:
        sql = 'SELECT ' + DB.ONOS_TBL + '.nodename, nodelist, ip_addr' + ' FROM ' + DB.ONOS_TBL + \
                ' INNER JOIN ' + DB.NODE_INFO_TBL + ' ON ' + DB.ONOS_TBL + '.nodename = ' + DB.NODE_INFO_TBL + '.nodename'

        nodes_info = conn.cursor().execute(sql).fetchall()

        if len(nodes_info) == 0:
            LOG.info('Fail to load onos list')
            return 'fail', pre_stat, reason

        # search data_ip
        data_ip = ''
        manage_ip = ''
        cpt_to_gw_packet = 0
        for nodename, nodelist, ip in nodes_info:
            if not nodelist == 'none':
                for node_info in eval(nodelist):
                    try:
                        if dict(node_info)['management_ip'] == node_ip:
                            manage_ip = ip
                            data_ip = dict(node_info)['data_ip']
                    except:
                        manage_ip = ''

                    if not manage_ip == '':
                        break
            if not manage_ip == '':
                break

        if data_ip == '':
            LOG.info('Can not find data ip')
            return 'fail', pre_stat, reason

        group_rt = SshCommand.onos_ssh_exec(manage_ip, 'groups')

        if group_rt is not None:
            for line in group_rt.splitlines():
                if '{tunnelDst=' + data_ip + '}' in line:
                    tmp = line.split(',')

                    for col in tmp:
                        if 'packets=' in col:
                            cpt_to_gw_packet = cpt_to_gw_packet + int(col.split('=')[1])

        if not dict(pre_stat).has_key(node_name + '_GW'):
            status = '-'
            json_ratio = {'current_rx': '-', 'current_compute_tx': '-', 'current_total': '-',
                          'ratio': '-',
                          'period': CONF.watchdog()['interval'], 'status': status, 'packet_loss': False,
                          'description': ''}
        else:
            cur_rx = rx - int(dict(pre_stat)[node_name + '_GW']['rx'])
            cur_total = gw_rx_sum - int(dict(pre_stat)[node_name + '_GW']['gw_rx_sum'])
            cur_packet = cpt_to_gw_packet - int(dict(pre_stat)[node_name + '_GW']['cpt_to_gw_packet'])

            if cur_rx == 0 and cur_total == 0:
                ratio = 100
            elif cur_rx <= 0 or cur_total < 0:
                ratio = 0
            else:
                ratio = float(cur_rx) * 100 / cur_total

            desc = 'GW RATIO = ' + str(ratio) + ' (' + str(cur_rx) + ' / ' + str(cur_total) + ')'

            loss_flag = False
            if cur_rx < cur_packet:
                LOG.info('GW Ratio Fail. (Data loss)')
                loss_flag = True

            LOG.info('GW Ratio = ' + str(ratio))

            if ratio < float(CONF.alarm()['gw_ratio']) or cur_rx < cur_packet:
                status = 'nok'

            json_ratio = {'current_rx': cur_rx, 'current_compute_tx': cur_packet, 'current_total': cur_total, 'ratio': format(ratio, '.2f'),
                          'period':CONF.watchdog()['interval'], 'status': status, 'packet_loss': loss_flag, 'description': desc}

        try:
            sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
                  ' SET gw_ratio = \"' + str(json_ratio) + '\"' + \
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE TRAFFIC GW INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] TRAFFIC GW DB Update Fail.')
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

    if not status == 'ok':
        reason = str(json_ratio)

    return status, pre_stat, reason


def get_gw_ratio_compute(conn, db_log, node_ip, node_name, pre_stat):
    status = 'ok'
    reason = ''

    try:
        sql = 'SELECT ' + DB.ONOS_TBL + '.nodename, nodelist, ip_addr' + ' FROM ' + DB.ONOS_TBL + \
                ' INNER JOIN ' + DB.NODE_INFO_TBL + ' ON ' + DB.ONOS_TBL + '.nodename = ' + DB.NODE_INFO_TBL + '.nodename'

        nodes_info = conn.cursor().execute(sql).fetchall()

        if len(nodes_info) == 0:
            LOG.info('Fail to load onos list')
            return 'fail', pre_stat, reason

        manage_ip = ''
        hostname = ''
        for nodename, nodelist, ip in nodes_info:
            if not nodelist == 'none':
                for node_info in eval(nodelist):
                    try:
                        if dict(node_info)['management_ip'] == node_ip:
                            manage_ip = ip
                            hostname = dict(node_info)['hostname']
                    except:
                        manage_ip = ''

                    if not manage_ip == '':
                        break
            if not manage_ip == '':
                break

        if hostname == '':
            LOG.info('Can not find hostname')
            return 'fail', pre_stat, reason

        try:
            sql = 'SELECT of_id FROM ' + DB.OPENSTACK_TBL + ' WHERE hostname = \'' + str(hostname) + '\''
            LOG.info(sql)
            node_info = conn.cursor().execute(sql).fetchone()

            of_id = node_info[0]
        except:
            LOG.exception()
            LOG.info('Can not find of_id')
            return 'fail', pre_stat, reason

        group_rt = SshCommand.onos_ssh_exec(manage_ip, 'groups')

        total_cnt = 0
        gw_list = []
        if group_rt is not None:
            for line in group_rt.splitlines():
                if of_id in line:
                    tmp = line.split(',')

                    for col in tmp:
                        if 'packets=' in col:
                            total_cnt = total_cnt + int(col.split('=')[1])
                            gw_list.append(int(col.split('=')[1]))

        str_ratio = ''

        if not dict(pre_stat).has_key(node_name + '_GW'):
            status = '-'
            json_ratio = {'ratio': '-', 'status': status, 'period':CONF.watchdog()['interval'], 'status': status}
        else:
            i = 0
            for gw in gw_list:
                cur_gw = gw - pre_stat[node_name + '_GW']['gw_list'][i]
                cur_total = total_cnt - pre_stat[node_name + '_GW']['gw_total']

                LOG.info('cur_gw = ' + str(cur_gw))
                LOG.info('cur_total = ' + str(cur_total))

                if cur_gw == 0 and cur_total == 0:
                    ratio = 100/len(gw_list)
                elif cur_gw <= 0 or cur_total <= 0:
                    ratio = 0
                else:
                    ratio = float(cur_gw) * 100 / cur_total

                i = i + 1
                str_ratio = str_ratio + str(ratio) + ':'

                if ratio < float(CONF.alarm()['gw_ratio']):
                    status = 'nok'

            json_ratio = {'ratio': str_ratio.rstrip(':'), 'status': status, 'period':CONF.watchdog()['interval'], 'status': status}
            LOG.info('[COMPUTE] ' + 'GW_RATIO = ' + str_ratio.rstrip(':'))

        try:
            sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
                  ' SET gw_ratio = \"' + str(json_ratio) + '\"' + \
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE TRAFFIC GW INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] TRAFFIC GW DB Update Fail.')
        except:
            LOG.exception()

        in_out_dic = dict()
        in_out_dic['gw_list'] = gw_list
        in_out_dic['gw_total'] = total_cnt

        pre_stat[node_name + '_GW'] = in_out_dic

        if not status == 'ok':
            reason = str(json_ratio)
    except:
        LOG.exception()
        status = 'fail'

    if not status == 'ok':
        reason = str(json_ratio)

    return status, pre_stat, reason


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


def get_node_traffic(conn, db_log, node_name, rx_dic, tx_dic, total_rx, total_tx, err_info, pre_stat):
    try:
        status = 'ok'
        reason_list = []

        pre_total_rx = total_rx
        pre_total_tx = total_tx

        # check minimum packet count
        sql = 'SELECT data_ip FROM ' + DB.OPENSTACK_TBL + ' WHERE nodename = \'' + node_name + '\''
        data_ip = conn.cursor().execute(sql).fetchone()[0]

        sql = 'SELECT ip_addr FROM ' + DB.NODE_INFO_TBL + ' WHERE type = \'ONOS\''
        nodes_info = conn.cursor().execute(sql).fetchall()

        min_rx = 0
        if len(nodes_info) == 0:
            LOG.info('Fail to load onos list')
            status = 'fail'
        else:
            for ip in nodes_info:
                flows_rt = SshCommand.onos_ssh_exec(ip[0], '\"flows --filter \'{tunnelDst=' + data_ip + '}\' --short\"')

                if flows_rt is not None:
                    for line in flows_rt.splitlines():
                        if 'tunnelDst' in line:
                            min_rx = min_rx + int(line.split(',')[2].split('=')[1])
                    break

        if not dict(pre_stat).has_key(node_name + '_VXLAN'):
            status = '-'
            ratio = -1
        else:
            total_rx = total_rx - int(dict(pre_stat)[node_name + '_VXLAN']['total_rx'])
            total_tx = total_tx - int(dict(pre_stat)[node_name + '_VXLAN']['total_tx'])
            cur_min = min_rx - int(dict(pre_stat)[node_name + '_VXLAN']['min_rx'])

            if total_rx == 0 and total_tx == 0:
                ratio = 100
            elif total_tx <= 0 or total_tx < 0:
                LOG.info('Node Traffic Ratio Fail.')
                ratio = 0
            else:
                ratio = float(total_rx) * 100 / total_tx

        LOG.info('Node Traffic Ratio = ' + str(ratio))

        port_json = {'rx': rx_dic[node_name], 'minimum_rx': min_rx, 'rx_drop': err_info['rx_drop'], 'rx_errs': err_info['rx_err'],
                      'tx': tx_dic[node_name], 'tx_drop': err_info['tx_drop'], 'tx_errs': err_info['tx_err']}

        description = ''

        if not status == '-':
            description = 'Ratio of success for all nodes = ' + str(ratio)  + ' (' + str(total_rx) + ' / ' + str(total_tx) + ')'

            if ratio < float(CONF.alarm()['node_traffic_ratio']):
                LOG.info('[NODE TRAFFIC] ratio nok')
                status = 'nok'

            if total_rx < cur_min:
                LOG.info('CUR_MIN_RX = ' + str(cur_min) + ', CUR_RX = ' + str(total_rx) + ', Less than rx minimum.')
                status = 'nok'

            if err_info['rx_drop'] - int(dict(pre_stat)[node_name + '_VXLAN']['rx_drop']) > 0:
                LOG.info('[NODE TRAFFIC] rx_drop nok')
                status = 'nok'

            if err_info['rx_err'] - int(dict(pre_stat)[node_name + '_VXLAN']['rx_err']) > 0:
                LOG.info('[NODE TRAFFIC] rx_err nok')
                status = 'nok'

            if err_info['tx_drop'] - int(dict(pre_stat)[node_name + '_VXLAN']['tx_drop']) > 0:
                LOG.info('[NODE TRAFFIC] tx_drop nok')
                status = 'nok'

            if err_info['tx_err'] - int(dict(pre_stat)[node_name + '_VXLAN']['tx_err']) > 0:
                LOG.info('[NODE TRAFFIC] tx_err nok')
                status = 'nok'

        in_out_dic = dict()
        in_out_dic['total_rx'] = pre_total_rx
        in_out_dic['total_tx'] = pre_total_tx

        in_out_dic['min_rx'] = min_rx

        in_out_dic['rx_drop'] = err_info['rx_drop']
        in_out_dic['rx_err'] = err_info['rx_err']
        in_out_dic['tx_drop'] = err_info['tx_drop']
        in_out_dic['tx_err'] = err_info['tx_err']

        pre_stat[node_name + '_VXLAN'] = in_out_dic
    except:
        LOG.exception()
        status = 'fail'

    vxlan_json = {'port_stat_vxlan': port_json, 'period': CONF.watchdog()['interval'],
                  'ratio': format(ratio, '.2f'), 'current_rx': total_rx, 'current_tx': total_tx,
                  'description': description, 'threshold': CONF.alarm()['node_traffic_ratio'], 'status': status}

    try:
        sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
              ' SET vxlan_traffic = \"' + str(vxlan_json) + '\"' + \
              ' WHERE nodename = \'' + node_name + '\''
        db_log.write_log('----- UPDATE VXLAN STAT INFO -----\n' + sql)

        if DB.sql_execute(sql, conn) != 'SUCCESS':
            db_log.write_log('[FAIL] VXLAN STAT DB Update Fail.')
    except:
        LOG.exception()

    if not status == 'ok':
        reason_list.append(vxlan_json)

    return status, pre_stat, str(reason_list)


def get_internal_traffic(conn, db_log, node_name, node_ip, user_name, sub_type, rx_count, patch_tx, pre_stat):
    try:
        status = 'ok'
        in_packet = 0
        out_packet = 0

        reason_list = []
        desc = ''

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

                port_json = {'vm_tx': inport_cnt, 'vxlan_rx': rx_count, 'out_gw': gw_cnt, 'output': output_cnt}
            else:
                port_json = {'vm_tx': -1, 'vxlan_rx': -1, 'out_gw': -1, 'output': -1}
                status = 'fail'

        else:
            port_json = {'vxlan_rx': rx_count, 'patch-integ': patch_tx}

            if patch_tx == -1:
                status = 'fail'
            else:
                in_packet = rx_count
                out_packet = patch_tx

        for_save_in = in_packet
        for_save_out = out_packet

        if not dict(pre_stat).has_key(node_name + '_internal'):
            status = '-'
            vxlan_json = {'port_stat_in_out': port_json, 'period': CONF.watchdog()['interval'],
                          'ratio': 0, 'current_rx': -1, 'current_tx': -1,
                          'description': desc, 'threshold': CONF.alarm()['internal_traffic_ratio'], 'status': status}
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
            desc = 'Internal Traffic Ratio = ' + str(ratio) + '(' + str(out_packet) + '/' + str(in_packet) + ')'

            if ratio < float(CONF.alarm()['internal_traffic_ratio']):
                status = 'nok'

            vxlan_json = {'port_stat_in_out': port_json, 'period': CONF.watchdog()['interval'],
                          'ratio': format(ratio, '.2f'), 'current_rx': in_packet, 'current_tx': out_packet,
                          'description': desc, 'threshold': CONF.alarm()['internal_traffic_ratio'], 'status': status}

        in_out_dic = dict()
        in_out_dic['in_packet'] = for_save_in
        in_out_dic['out_packet'] = for_save_out
        pre_stat[node_name + '_internal'] = in_out_dic

        try:
            sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
                  ' SET internal_traffic = \"' + str(vxlan_json) + '\"' + \
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE INTERNAL TRAFFIC INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] INTERNAL TRAFFIC DB Update Fail.')
        except:
            LOG.exception()
    except:
        LOG.exception()
        status = 'fail'

    if not status == 'ok':
        reason_list.append(vxlan_json)

    return status, pre_stat, str(reason_list)

