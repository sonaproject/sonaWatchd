from subprocess import Popen, PIPE
import csv

from api.sona_log import LOG
from api.watcherdb import DB
from api.config import CONF
from api.sbapi import SshCommand


def onos_app_check(node):

    app_rt = SshCommand.onos_ssh_exec(node, 'apps -a -s')

    app_active_list = list()
    if app_rt is not None:
        for line in app_rt.splitlines():
            app_active_list.append(line.split(".")[2].split()[0])

        if set(CONF.onos()['app_list']).issubset(app_active_list):
            return 'ok', app_rt
        else:
            LOG.error("\'%s\' Application Check Error", node)
            return 'nok', app_rt
    else:
        LOG.error("\'%s\' Application Check Error", node)
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
            LOG.error("\'%s\' Connection Check Error", node_ip)
            of_status = 'fail'
            ovsdb_status = 'fail'

        if nodes_rt is not None:
            cluster_status = 'ok'
            for line in nodes_rt.splitlines():
                if not ('state=READY' in line):
                    cluster_status = 'nok'
        else:
            LOG.error("\'%s\' Connection Check Error", node_ip)
            cluster_status = 'fail'

        try:
            sql = 'UPDATE ' + DB.ONOS_TBL + \
                  ' SET ovsdb = \'' + str_ovsdb + '\',' + \
                  ' of = \'' + str_of + '\',' + \
                  ' cluster = \'' + str(nodes_rt) + '\'' \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update Connection info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('DB Update Fail.')
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
                LOG.error('DB Update Fail.')
        except:
            LOG.exception()

        return web_status
    except:
        LOG.exception()
        return 'fail'


def onos_ha_check(conn):
    try:
        stats_url = 'http://10.10.2.114:8282/haproxy_stats;csv'
        stats_user = 'haproxy'
        stats_passwd = 'telcowr1'

        cmd = 'curl --user ' + stats_user + ':' + stats_passwd + ' --header \'Accept: text/html, application/xhtml+xml, image/jxr, */*\' \"' + stats_url + '\"'
        result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, error = result.communicate()

        if result.returncode != 0:
            LOG.error("Cmd Fail, cause => %s", error)
        else:
            report_data = csv.DictReader(output.lstrip('# ').splitlines())

        dic_stat = dict()
        for row in report_data:
            if row['pxname'].strip() == 'stats' or row['svname'].strip() == 'BACKEND':
                continue

            dtl_list = {'name': row['svname'], 'req_count': row['stot'], 'succ_count': row['hrsp_2xx'], 'node_sts': row['status']}

            svc_type = row['pxname']

            if (dic_stat.has_key(svc_type)):
                dic_stat[svc_type].append(dtl_list)
            else:
                dic_stat[svc_type] = list()
                dic_stat[svc_type].append(dtl_list)

        try:
            str_dic_stat = str(dic_stat)

            sql = 'UPDATE ' + DB.HA_TBL + \
                  ' SET stats = \"' + str_dic_stat + '\"' + \
                  ' WHERE ha_key = \"' + 'HA' + '\"'
            LOG.info('Update HA info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('DB Update Fail.')
        except:
            LOG.exception()

        return dic_stat
    except:
        LOG.exception()
        return None


def get_ha_stats(conn, ha_dic, node_name):
    try:
        ha_status = 'ok'
        ha_ratio = 'ok'

        str_list = ''

        frontend = 0
        backend = 0

        for key in dict(ha_dic).keys():
            for line in ha_dic[key]:
                host = dict(line)['name']

                if host.lower() == node_name.lower():
                    status = dict(line)['node_sts']

                    if not 'UP' in status:
                        ha_status = 'nok'

                        str_list = str_list + key + ' : ' + status + '\n'

                if host == 'FRONTEND':
                    frontend = int(dict(line)['req_count'])
                else:
                    backend = backend + int(dict(line)['succ_count'])

        ratio = float(backend) * 100 / frontend

        if ratio < float(CONF.alarm()['ha_proxy']):
            ha_ratio = 'nok'

        try:
            sql = 'UPDATE ' + DB.ONOS_TBL + \
                  ' SET haproxy = \'' + str_list + '\'' + \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update HA info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('DB Update Fail.')
        except:
            LOG.exception()

        return ha_status, ha_ratio
    except:
        LOG.exception()
        return 'fail', 'fail'


def onos_node_check(conn, node_name, node_ip):
    try:
        node_rt = SshCommand.onos_ssh_exec(node_ip, 'openstack-nodes')

        node_status = 'ok'

        str_port = ''

        if node_rt is not None:
            for line in node_rt.splitlines():
                if line.startswith('hostname'):
                    if not 'init=COMPLETE' in line:
                        node_status = 'nok'

                    host_name = line.split(',')[0].split('=')[1]
                    of_id = line.split(',')[4].split('=')[1]

                    try:
                        sql = 'INSERT OR REPLACE INTO ' + DB.OF_TBL + '(hostname, of_id)' + \
                              ' VALUES (\'' + host_name + '\',\'' + of_id + '\')'

                        if DB.sql_execute(sql, conn) != 'SUCCESS':
                            LOG.error('DB Update Fail.')
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
                LOG.error('DB Update Fail.')
        except:
            LOG.exception()

        return node_status
    except:
        LOG.exception()
        return 'fail'

