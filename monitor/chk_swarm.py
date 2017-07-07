from api.sona_log import LOG
from api.watcherdb import DB
from api.sbapi import SshCommand
from api.config import CONF

def swarm_check(conn, db_log, node_name, user_name, node_ip):
    str_node = ''
    str_service = ''
    str_ps = ''

    ret_app = 'ok'
    ret_node = 'ok'

    node_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo docker node ls')

    if node_rt is not None:
        try:
            leader_flag = False
            for line in node_rt.splitlines():
                line = line.decode('utf-8')
                str_node = str_node + line + '\n'

                if line.startswith('ID'):
                    continue

                if 'Leader' in line:
                    leader_flag = True

                    if not ('Ready' in line and 'Active' in line):
                        ret_node = 'nok'
                        break

                if 'Down' in line:
                    ret_node = 'nok'
                    break

            if not leader_flag:
                ret_node = 'nok'
        except:
            LOG.exception()
            ret_node = 'nok'

    else:
        LOG.error("\'%s\' Swarm Node Check Error", node_ip)
        str_node = 'fail'

    service_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo docker service ls')

    if service_rt is not None:
        try:
            for app in CONF.swarm()['app_list']:
                find_flag = False
                for line in service_rt.splitlines():
                    line = line.decode('utf-8')

                    if line.startswith('ID'):
                        continue

                    id, name, mode, rep, img = line.split()

                    if app == name:
                        find_flag = True
                        rep_tmp = rep.split('/')

                        if not (rep_tmp[0] == rep_tmp[1]):
                            ret_app = 'nok'
                            break

                if not find_flag:
                    ret_app = 'nok'
                    break
        except:
            LOG.exception()
            ret_app = 'nok'

        for line in service_rt.splitlines():
            line = line.decode('utf-8')
            str_service = str_service + line + '\n'
    else:
        LOG.error("\'%s\' Swarm Service Check Error", node_ip)
        str_service = 'fail'
        ret_app = 'nok'

    try:
        for app in CONF.swarm()['app_list']:
            ps_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo docker service ps ' + app)

            str_ps = str_ps + ' * ' + app + '\n\n'

            if ps_rt is not None:
                for line in ps_rt.splitlines():
                    line = line.decode('utf-8')
                    str_ps = str_ps + line + '\n'
            else:
                LOG.error("\'%s\' Swarm PS Check Error", node_ip)
                str_ps = str_ps + 'Command failure(' + app + ')\n'

            str_ps = str_ps + '\n'
    except:
        LOG.exception()

    try:
        sql = 'UPDATE ' + DB.SWARM_TBL + \
              ' SET node = \'' + str_node + '\',' + \
              ' service = \'' + str_service + '\',' + \
              ' ps = \'' + str_ps + '\'' + \
              ' WHERE nodename = \'' + node_name + '\''
        db_log.write_log('----- UPDATE SWARM INFO -----\n' + sql)

        if DB.sql_execute(sql, conn) != 'SUCCESS':
            db_log.write_log('[FAIL] SWARN DB Update Fail.')
    except:
        LOG.exception()

    return ret_app, ret_node