from api.sona_log import LOG
from api.watcherdb import DB
from api.config import CONF
from api.sbapi import SshCommand


def onos_app_check(conn, db_log, node_name, node_ip):
    try:
        app_rt = SshCommand.onos_ssh_exec(node_ip, 'apps -a -s')

        status = 'ok'
        app_active_list = list()

        app_list = []
        fail_reason = []

        if app_rt is not None:
            for line in app_rt.splitlines():
                app_active_list.append(line.split(".")[2].split()[0])

            if not 'cpman' in app_active_list:
                # activate cpman
                LOG.info('Cpman does not exist. Activate cpman')
                SshCommand.onos_ssh_exec(node_ip, 'app activate org.onosproject.cpman')

            for app in CONF.onos()['app_list']:
                if app in app_active_list:
                    app_json = {'name': app, 'status': 'ok', 'monitor_item': True}
                    app_active_list.remove(app)
                else:
                    status = 'nok'
                    app_json = {'name': app, 'status': 'nok', 'monitor_item': True}
                    fail_reason.append(app_json)
                app_list.append(app_json)

            for app in app_active_list:
                app_json = {'name': app, 'status': 'ok', 'monitor_item': False}
                app_list.append(app_json)
        else:
            LOG.error("\'%s\' ONOS Application Check Error", node_ip)
            status = 'fail'
            app_list = 'fail'

        try:
            sql = 'UPDATE ' + DB.ONOS_TBL + \
                  ' SET applist = \"' + str(app_list) + '\"' +\
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE ONOS APP INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] ONOS APP DB Update Fail.')
        except:
            LOG.exception()
    except:
        LOG.exception()
        status = 'fail'
        fail_reason = 'fail'

    return status, str(fail_reason)


def onos_rest_check(conn, db_log, node_name, node_ip):
    try:
        web_status = 'ok'

        web_list = []
        fail_reason = []

        web_rt = SshCommand.onos_ssh_exec(node_ip, 'web:list')

        if web_rt is not None:
            for web in CONF.onos()['rest_list']:
                for line in web_rt.splitlines():
                    if line.startswith('ID') or line.startswith('--'):
                        continue

                    if ' ' + web + ' ' in line:
                        if not ('Active' in line and 'Deployed' in line):
                            rest_json = {'name': web, 'status': 'nok', 'monitor_item': True}
                            fail_reason.append(rest_json)
                            web_status = 'nok'
                        else:
                            rest_json = {'name': web, 'status': 'ok', 'monitor_item': True}

                        web_list.append(rest_json)

            for line in web_rt.splitlines():
                if line.startswith('ID') or line.startswith('--'):
                    continue

                name = " ".join(line.split()).split(' ')[10]

                if not name in CONF.onos()['rest_list']:
                    if not ('Active' in line and 'Deployed' in line):
                        rest_json = {'name': name, 'status': 'nok', 'monitor_item': False}
                    else:
                        rest_json = {'name': name, 'status': 'ok', 'monitor_item': False}

                    web_list.append(rest_json)
        else:
            LOG.error("\'%s\' ONOS Rest Check Error", node_ip)
            web_status = 'fail'
            web_list = 'fail'
            fail_reason = 'fail'

        try:
            sql = 'UPDATE ' + DB.ONOS_TBL + \
                  ' SET weblist = \"' + str(web_list) + '\"' +\
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE ONOS REST INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] ONOS REST DB Update Fail.')
        except:
            LOG.exception()

    except:
        LOG.exception()
        web_status = 'fail'
        fail_reason = 'fail'

    return web_status, str(fail_reason)


def parse_openflow(line, hostname, is_monitor):
    of_id = line.split(',')[0].split('=')[1]
    available = line.split(',')[1].split('=')[1]
    status = line.split(',')[2].split('=')[1].split(' ')[0]
    role = line.split(',')[3].split('=')[1]
    type = line.split(',')[4].split('=')[1]

    rest_json = {'hostname': hostname, 'available': available, 'status': status,
                 'role': role, 'type': type, 'monitor_item': is_monitor}

    return rest_json

def onos_conn_check(conn, db_log, node_name, node_ip):
    try:
        device_rt = SshCommand.onos_ssh_exec(node_ip, 'devices')
        nodes_rt = SshCommand.onos_ssh_exec(node_ip, 'nodes')

        of_status = 'ok'

        of_list = []
        of_fail_reason = []

        cluster_fail_reason = ''

        find_list = []
        if device_rt is not None:
            try:
                sql = 'SELECT hostname, of_id FROM ' + DB.OPENSTACK_TBL
                nodes_info = conn.cursor().execute(sql).fetchall()

                for hostname, switch_id in nodes_info:
                    for line in device_rt.splitlines():
                        if line.startswith('id=of'):
                            find_list.append(of_id)
                            of_id = line.split(',')[0].split('=')[1]
                            available = line.split(',')[1].split('=')[1]
                            status = line.split(',')[2].split('=')[1].split(' ')[0]
                            role = line.split(',')[3].split('=')[1]
                            type = line.split(',')[4].split('=')[1]

                            if switch_id == of_id:
                                rest_json = {'hostname': hostname, 'available': available, 'status': status,
                                             'role': role, 'type': type, 'monitor_item': True}

                                if available == 'true':
                                    of_status = 'nok'
                                    of_fail_reason.append(rest_json)

                                of_list.append(rest_json)

                for line in device_rt.splitlines():
                    if line.startswith('id=of'):
                        of_id = line.split(',')[0].split('=')[1]
                        available = line.split(',')[1].split('=')[1]
                        status = line.split(',')[2].split('=')[1].split(' ')[0]
                        role = line.split(',')[3].split('=')[1]
                        type = line.split(',')[4].split('=')[1]

                        if not of_id in find_list:
                            rest_json = {'hostname': hostname, 'available': available, 'status': status,
                                         'role': role, 'type': type, 'monitor_item': False}
                            of_list.append(rest_json)

            except:
                LOG.exception()
                LOG.error("\'%s\' Connection Check Error(devices)", node_ip)
                of_status = 'fail'
                of_fail_reason = 'fail'
        else:
            LOG.error("\'%s\' Connection Check Error(devices)", node_ip)
            of_status = 'fail'
            of_fail_reason = 'fail'

        if nodes_rt is not None:
            cluster_status = 'ok'
            for line in nodes_rt.splitlines():
                if not ('state=READY' in line):
                    cluster_status = 'nok'
                    cluster_fail_reason = cluster_fail_reason + line.split(',')[0].split('=')[0] + '[nok],'
        else:
            LOG.error("\'%s\' Connection Check Error(nodes)", node_ip)
            cluster_status = 'fail'

        try:
            sql = 'UPDATE ' + DB.ONOS_TBL + \
                  ' SET openflow = \"' + str(of_list) + '\",' + \
                  ' cluster = \'' + str(nodes_rt) + '\'' \
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE ONOS CONNECTION INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] ONOS CONNECTION DB Update Fail.')
        except:
            LOG.exception()
    except:
        LOG.exception()
        of_status = 'fail'
        cluster_status = 'fail'

    return of_status, cluster_status, str(of_fail_reason), cluster_fail_reason



def onos_node_check(conn, db_log, node_name, node_ip):
    try:
        node_rt = SshCommand.onos_ssh_exec(node_ip, 'openstack-nodes')
        str_node_list = ''

        node_status = 'ok'
        fail_reason = ''

        str_port = ''

        if node_rt is not None:
            for ip in CONF.openstack()['compute_list'] + CONF.openstack()['gateway_list']:
                ip = str(ip).split(':')[1]

                find_flag = False

                for line in node_rt.splitlines():
                    if (not (line.startswith('Total') or line.startswith('Hostname'))) and ' ' + ip + ' ' in line:
                        find_flag = True
                        fail_flag = False
                        new_line = " ".join(line.split())
                        str_node_list = str_node_list + new_line + '\n'

                        tmp = new_line.split(' ')
                        host_name = tmp[0]
                        of_id = tmp[2]

                        if not 'COMPLETE' in line:
                            node_status = 'nok'
                            fail_flag = True

                        try:
                            sql = 'SELECT nodename FROM ' + DB.NODE_INFO_TBL + ' WHERE ip_addr = \'' + ip + '\''
                            openstack_nodename = conn.cursor().execute(sql).fetchone()[0]

                            if tmp[3].startswith('of:'):
                                data_ip = tmp[5]
                            else:
                                data_ip = tmp[4]

                            sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
                                  ' SET data_ip = \'' + data_ip + '\',' + \
                                  ' hostname = \'' + host_name + '\',' + \
                                  ' of_id = \'' + of_id + '\'' + \
                                  ' WHERE nodename = \'' + openstack_nodename + '\''
                            db_log.write_log('----- UPDATE OPENSTACK INFO -----\n' + sql)

                            if DB.sql_execute(sql, conn) != 'SUCCESS':
                                db_log.write_log('[FAIL] OPENSTACK MANAGE IP Update Fail.')
                        except:
                            LOG.exception()

                        port_rt = SshCommand.onos_ssh_exec(node_ip, 'openstack-node-check ' + host_name)

                        str_port = str_port + '\n* ' + host_name + '\n'

                        if port_rt is not None:
                            for port_line in port_rt.splitlines():
                                str_port = str_port + port_line + '\n'

                                if port_line.startswith('[') or port_line.strip() == '':
                                    continue

                                if not port_line.startswith('OK'):
                                    node_status = 'nok'
                                    fail_flag = True
                        else:
                            node_status = 'nok'
                            str_port = 'fail'

                        if fail_flag:
                            fail_reason = fail_reason + host_name + '[nok],'

                if not find_flag:
                    node_status = 'nok'
                    fail_reason = fail_reason + ip + '[nok],'
                    str_node_list = str_node_list + ip + ' - - - - NO_EXIST' + '\n'
        else:
            LOG.error("\'%s\' ONOS Node Check Error", node_ip)
            node_status = 'fail'
            str_node_list = 'fail'
            fail_reason = 'fail'

        try:
            sql = 'UPDATE ' + DB.ONOS_TBL + \
                  ' SET nodelist = \'' + str_node_list + '\',' + \
                  ' port = \'' + str_port + '\'' \
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE ONOS NODE INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] ONOS NODE Update Fail.')
        except:
            LOG.exception()
    except:
        LOG.exception()
        node_status = 'fail'
        fail_reason = 'fail'

    return node_status, fail_reason.rstrip(',')


def controller_traffic_check(conn, db_log, node_name, node_ip, pre_stat):
    try:
        summary_rt = SshCommand.onos_ssh_exec(node_ip, 'summary')

        in_packet = 0
        out_packet = 0
        str_info = ''
        controller_traffic = 'ok'
        reason = ''

        if summary_rt is not None:
            data_ip = str(summary_rt).split(',')[0].split('=')[1]

            try:
                sql = 'SELECT hostname, of_id FROM ' + DB.OPENSTACK_TBL
                nodes_info = conn.cursor().execute(sql).fetchall()

                str_info = ''

                for hostname, of_id in nodes_info:
                    cmd = 'cpman-stats-list ' + data_ip + ' control_message ' + of_id

                    stat_rt = SshCommand.onos_ssh_exec(node_ip, cmd)

                    if stat_rt is not None:
                        str_info = str_info + 'HOST_NAME=' + hostname + ', SWITCH_ID=' + of_id

                        if not str(stat_rt).startswith('Failed'):
                            for line in stat_rt.splitlines():
                                type = line.split(',')[0].split('=')[1]
                                avg_cnt = int(line.split(',')[2].split('=')[1])

                                str_info = str_info  + ', ' + type + '=' + str(avg_cnt)

                                if type == 'INBOUND_PACKET':
                                    in_packet = in_packet + avg_cnt
                                elif type == 'OUTBOUND_PACKET':
                                    out_packet = out_packet + avg_cnt

                            str_info = str_info + '\n'

                for_save_in = in_packet
                for_save_out = out_packet

                if not dict(pre_stat).has_key(node_name):
                    controller_traffic = '-'

                    in_out_dic = dict()
                    in_out_dic['in_packet'] = for_save_in
                    in_out_dic['out_packet'] = for_save_out

                    pre_stat[node_name] = in_out_dic
                else:
                    in_packet = in_packet - int(dict(pre_stat)[node_name]['in_packet'])
                    out_packet = out_packet - int(dict(pre_stat)[node_name]['out_packet'])

                    if in_packet <= CONF.alarm()['controller_traffic_minimum_inbound']:
                        reason = ' * Minimum increment for status check = ' + str(
                            CONF.alarm()['controller_traffic_minimum_inbound'])
                        str_info = str_info + reason
                        controller_traffic = '-'
                    else:
                        if in_packet == 0 and out_packet == 0:
                            ratio = 100
                        elif in_packet <= 0 or out_packet < 0:
                            LOG.info('Controller Traffic Ratio Fail.')
                            ratio = 0
                        else:
                            ratio = float(out_packet) * 100 / in_packet

                        LOG.info('[CPMAN][' + node_name + '] Controller Traffic Ratio = ' + str(ratio) + '(' + str(out_packet) + '/' + str(in_packet) + ')')
                        str_info = str_info + ' * [LAST ' + str(CONF.watchdog()['interval']) + ' Sec] Controller Traffic Ratio = ' + str(ratio) + '(' + str(out_packet) + '/' + str(in_packet) + ')\n'

                        if ratio < float(CONF.alarm()['controller_traffic_ratio']):
                            controller_traffic = 'nok'
                            reason = 'controller traffic ratio : ' + str(format(ratio, '.2f'))

                        in_out_dic = dict()
                        in_out_dic['in_packet'] = for_save_in
                        in_out_dic['out_packet'] = for_save_out

                        pre_stat[node_name] = in_out_dic
            except:
                LOG.exception()
                controller_traffic = 'fail'
                reason = 'fail'
        else:
            controller_traffic = 'fail'
            reason = 'fail'

        try:
            sql = 'UPDATE ' + DB.ONOS_TBL + \
                  ' SET traffic_stat = \'' + str_info.rstrip('\n') + '\'' + \
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE CONTROLLER TRAFFIC INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] CONTROLLER TRAFFIC Update Fail.')
        except:
            LOG.exception()
    except:
        controller_traffic = 'fail'
        reason = 'fail'

    return controller_traffic, pre_stat, reason
