from api.sona_log import LOG
from api.watcherdb import DB
from api.config import CONF
from api.sbapi import SshCommand


def onos_app_check(conn, db_log, node_name, node_ip):
    try:

        app_rt = SshCommand.onos_ssh_exec(node_ip, 'apps -a -s')

        status = 'ok'
        applist = ''
        app_active_list = list()
        if app_rt is not None:
            for line in app_rt.splitlines():
                app_active_list.append(line.split(".")[2].split()[0])

            if not 'cpman' in app_active_list:
                # activate cpman
                LOG.info('Cpman does not exist. Activate cpman')
                SshCommand.onos_ssh_exec(node_ip, 'app activate org.onosproject.cpman')

            for app in CONF.onos()['app_list']:
                if app in app_active_list:
                    applist = applist + str(app).ljust(30) + '[ok]\n'
                else:
                    applist = applist + str(app).ljust(30) + '[nok]\n'
                    status = 'nok'
        else:
            LOG.error("\'%s\' ONOS Application Check Error", node_ip)
            status = 'fail'
            applist = 'fail'

        try:
            sql = 'UPDATE ' + DB.ONOS_TBL + \
                  ' SET applist = \'' + applist + '\'' +\
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE ONOS APP INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] ONOS APP DB Update Fail.')
        except:
            LOG.exception()
    except:
        LOG.exception()
        status = 'fail'

    return status


def onos_rest_check(conn, db_log, node_name, node_ip):
    try:
        weblist = ''
        web_status = 'ok'

        web_rt = SshCommand.onos_ssh_exec(node_ip, 'web:list')

        if web_rt is not None:
            for app in CONF.onos()['rest_list']:
                for line in web_rt.splitlines():
                    if line.startswith('ID') or line.startswith('--'):
                        continue

                    if ' ' + app + ' ' in line:
                        if not ('Active' in line and 'Deployed' in line):
                            weblist = weblist + str(app).ljust(30) + '[nok]\n'
                            web_status = 'nok'
                        else:
                            weblist = weblist + str(app).ljust(30) + '[ok]\n'

        else:
            LOG.error("\'%s\' ONOS Rest Check Error", node_ip)
            web_status = 'fail'
            weblist = 'fail'

        try:
            sql = 'UPDATE ' + DB.ONOS_TBL + \
                  ' SET weblist = \'' + weblist + '\'' +\
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE ONOS REST INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] ONOS REST DB Update Fail.')
        except:
            LOG.exception()

        return web_status
    except:
        LOG.exception()
        return 'fail'


def onos_conn_check(conn, db_log, node_name, node_ip):
    try:
        device_rt = SshCommand.onos_ssh_exec(node_ip, 'devices')
        nodes_rt = SshCommand.onos_ssh_exec(node_ip, 'nodes')

        str_of = ''

        if device_rt is not None:
            of_status = 'ok'
            for line in device_rt.splitlines():
                if line.startswith('id=of'):
                    if not ('available=true' in line):
                        of_status = 'nok'

                    of_id = line.split(',')[0].split('=')[1]

                    try:
                        sql = 'SELECT hostname FROM ' + DB.OF_TBL + ' WHERE of_id = \'' + of_id + '\''
                        node_info = conn.cursor().execute(sql).fetchone()

                        line = line.replace(of_id, node_info[0] + '(' + of_id + ')')
                    except:
                        LOG.exception()

                    str_of = str_of + line + '\n'
        else:
            LOG.error("\'%s\' Connection Check Error(devices)", node_ip)
            of_status = 'fail'

        if nodes_rt is not None:
            cluster_status = 'ok'
            for line in nodes_rt.splitlines():
                if not ('state=READY' in line):
                    cluster_status = 'nok'
        else:
            LOG.error("\'%s\' Connection Check Error(nodes)", node_ip)
            cluster_status = 'fail'

        try:
            sql = 'UPDATE ' + DB.ONOS_TBL + \
                  ' SET openflow = \'' + str_of + '\',' + \
                  ' cluster = \'' + str(nodes_rt) + '\'' \
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE ONOS CONNECTION INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] ONOS CONNECTION DB Update Fail.')
        except:
            LOG.exception()

        return of_status, cluster_status
    except:
        LOG.exception()
        return 'fail', 'fail'


def onos_node_check(conn, db_log, node_name, node_ip):
    try:
        node_rt = SshCommand.onos_ssh_exec(node_ip, 'openstack-nodes')

        node_status = 'ok'

        str_port = ''

        if node_rt is not None:
            for line in node_rt.splitlines():
                if not (line.startswith('Total') or line.startswith('Hostname')):
                    if not 'COMPLETE' in line:
                        node_status = 'nok'

                    new_line = " ".join(line.split())

                    tmp = new_line.split(' ')
                    host_name = tmp[0]
                    of_id = tmp[2]

                    try:
                        sql = 'INSERT OR REPLACE INTO ' + DB.OF_TBL + '(hostname, of_id)' + \
                              ' VALUES (\'' + host_name + '\',\'' + of_id + '\')'

                        if DB.sql_execute(sql, conn) != 'SUCCESS':
                            LOG.error('OF(node) DB Update Fail.')
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
                    else:
                        node_status = 'nok'
                        str_port = 'fail'
        else:
            LOG.error("\'%s\' ONOS Node Check Error", node_ip)
            node_status = 'nok'
            node_rt = 'fail'

        try:
            sql = 'UPDATE ' + DB.ONOS_TBL + \
                  ' SET nodelist = \'' + str(node_rt) + '\',' + \
                  ' port = \'' + str_port + '\'' \
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE ONOS NODE INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] ONOS NODE Update Fail.')
        except:
            LOG.exception()

        return node_status
    except:
        LOG.exception()
        return 'fail'


def controller_traffic_check(conn, db_log, node_name, node_ip, pre_stat):
    try:
        summary_rt = SshCommand.onos_ssh_exec(node_ip, 'summary')

        in_packet = 0
        out_packet = 0
        str_info = ''
        controller_traffic = 'ok'

        if summary_rt is not None:
            data_ip = str(summary_rt).split(',')[0].split('=')[1]

            try:
                sql = 'SELECT hostname, of_id FROM ' + DB.OF_TBL
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
                                    LOG.info('[CPMAN] HOST_NAME = ' + hostname + ', IN_PACKET = ' + str(avg_cnt))
                                elif type == 'OUTBOUND_PACKET':
                                    out_packet = out_packet + avg_cnt
                                    LOG.info('[CPMAN] HOST_NAME = ' + hostname + ', OUT_PACKET = ' + str(avg_cnt))

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
                        str_info = str_info + ' * Minimum increment for status check = ' + str(CONF.alarm()['controller_traffic_minimum_inbound'])
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

                        in_out_dic = dict()
                        in_out_dic['in_packet'] = for_save_in
                        in_out_dic['out_packet'] = for_save_out

                        pre_stat[node_name] = in_out_dic
            except:
                LOG.exception()
                controller_traffic = 'nok'
        else:
            controller_traffic = 'nok'

        try:
            sql = 'UPDATE ' + DB.ONOS_TBL + \
                  ' SET traffic_stat = \'' + str_info.rstrip('\n') + '\'' + \
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE CONTROLLER TRAFFIC INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] CONTROLLER TRAFFIC Update Fail.')
        except:
            LOG.exception()

        return controller_traffic, pre_stat
    except:
        LOG.exception()
        return 'fail'
