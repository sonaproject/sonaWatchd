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
                    str_of = str_of + line + '\n'
                    if not ('available=true' in line):
                        of_status = 'nok'
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
            sql = 'UPDATE ' + DB.CONNECTION_TBL + \
                  ' SET ovsdb = \'' + str_ovsdb + '\',' + \
                  ' of = \'' + str_of + '\',' + \
                  ' cluster = \'' + nodes_rt + '\'' \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update Resource info = ' + sql)

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
                  ' SET weblist = \'' + web_rt + '\'' +\
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

