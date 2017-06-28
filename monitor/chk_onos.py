from subprocess import Popen, PIPE
import csv

from api.sona_log import LOG
from api.watcherdb import DB
from api.config import CONF
from api.sbapi import SshCommand


def onos_app_check(node):
    try:
        app_rt = SshCommand.onos_ssh_exec(node, 'apps -a -s')

        app_active_list = list()
        if app_rt is not None:
            for line in app_rt.splitlines():
                app_active_list.append(line.split(".")[2].split()[0])

            if not 'cpman' in app_active_list:
                # activate cpman
                LOG.info('Cpman does not exist. Activate cpman')
                SshCommand.onos_ssh_exec(node, 'app activate org.onosproject.cpman')

            if set(CONF.onos()['app_list']).issubset(app_active_list):
                return 'ok', app_rt
            else:
                LOG.error("\'%s\' Application Check Error", node)
                return 'nok', app_rt
        else:
            LOG.error("\'%s\' Application Check Error", node)
            return 'nok', 'fail'
    except:
        LOG.exception()
        return 'nok', 'fail'


def onos_conn_check(conn, node_name, node_ip):
    try:
        device_rt = SshCommand.onos_ssh_exec(node_ip, 'devices')
        nodes_rt = SshCommand.onos_ssh_exec(node_ip, 'nodes')

        str_ovsdb = ''
        str_of = ''

        if device_rt is not None:
            of_status = 'ok'
            ovsdb_status = 'ok'
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

                elif line.startswith('id=ovsdb'):
                    str_ovsdb = str_ovsdb + line + '\n'
                    if not ('available=true, local-status=connected' in line):
                        ovsdb_status = 'nok'
        else:
            LOG.error("\'%s\' Connection Check Error(devices)", node_ip)
            of_status = 'fail'
            ovsdb_status = 'fail'

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
                  ' SET ovsdb = \'' + str_ovsdb + '\',' + \
                  ' openflow = \'' + str_of + '\',' + \
                  ' cluster = \'' + str(nodes_rt) + '\'' \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update Connection info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('ONOS(conn) DB Update Fail.')
        except:
            LOG.exception()

        return of_status, ovsdb_status, cluster_status
    except:
        LOG.exception()
        return 'fail', 'fail', 'fail'


def onos_web_check(conn, node_name, node_ip):
    try:
        web_rt = SshCommand.onos_ssh_exec(node_ip, 'web:list')

        if web_rt is not None:
            web_status = 'ok'
            for line in web_rt.splitlines():
                if line.startswith('ID') or line.startswith('--'):
                    continue

                if not ('Active' in line and 'Deployed' in line):
                    web_status = 'nok'
        else:
            LOG.error("\'%s\' Web Check Error", node_ip)
            web_status = 'fail'

        try:
            sql = 'UPDATE ' + DB.ONOS_TBL + \
                  ' SET weblist = \'' + str(web_rt) + '\'' +\
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update Resource info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('ONOS(web) DB Update Fail.')
        except:
            LOG.exception()

        return web_status
    except:
        LOG.exception()
        return 'fail'


def onos_node_check(conn, node_name, node_ip):
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
            LOG.info('Update Resource info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('ONOS(node) DB Update Fail.')
        except:
            LOG.exception()

        return node_status
    except:
        LOG.exception()
        return 'fail'


def controller_traffic_check(conn, node_name, node_ip, pre_stat):
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
                else:
                    in_packet = in_packet - int(dict(pre_stat)[node_name]['in_packet'])
                    out_packet = out_packet - int(dict(pre_stat)[node_name]['out_packet'])

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
            LOG.info('Update Controller Traffic info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('ONOS(traffic_stat) DB Update Fail.')
        except:
            LOG.exception()

        return controller_traffic, pre_stat
    except:
        LOG.exception()
        return 'fail'
