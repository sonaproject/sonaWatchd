from subprocess import Popen, PIPE
import json

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


def find_swarm_manager():
    hostname = ''

    try:
        url = CONF.xos()['xos_rest_server']
        account = CONF.xos()['xos_rest_account']

        cmd = 'curl -H "Accept: application/json; indent=4" -u ' + account + ' -X GET ' + url + '/api/core/controllers/'
        result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, error = result.communicate()

        if result.returncode != 0:
            LOG.error("Cmd Fail, cause => %s", error)
            return ''

        controller_array = json.loads(output)

        for controller_info in controller_array:
            auth_url = controller_info['auth_url']

            LOG.info('swarm_manager_auth_url = ' + auth_url)

            tmp = str(auth_url).split(':')

            hostname = tmp[0]
            break
    except:
        LOG.exception()

    return hostname


def get_service_list():
    service_list = []

    try:
        url = CONF.xos()['xos_rest_server']
        account = CONF.xos()['xos_rest_account']

        cmd = 'curl -H "Accept: application/json; indent=4" -u ' + account + ' -X GET ' + url + '/api/core/instances/'
        result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, error = result.communicate()

        if result.returncode != 0:
            LOG.error("Cmd Fail, cause => %s", error)
            return ''

        instance_array = json.loads(output)

        for instance_info in instance_array:
            name = instance_info['instance_name']

            LOG.info('swarm_instance_name = ' + name)

            service_list.append(name)

    except:
        LOG.exception()

    return service_list


def swarm_node_check(conn, db_log, node_name, username, node_ip, swarm_manager):
    node_status = 'ok'
    node_list = []
    fail_reason = []

    try:
        cmd = 'ssh root@' + swarm_manager + ' \"sudo docker node ls\"'
        node_rt = SshCommand.ssh_exec(username, node_ip, cmd)

        if node_rt is not None:
            try:
                leader_flag = False
                for line in node_rt.splitlines():
                    line = line.decode('utf-8')

                    line = " ".join(line.replace('*', '').split())
                    tmp = line.split(' ')

                    if line.startswith('ID'):
                        continue

                    if 'Leader' in line:
                        node_json = {'hostname': tmp[1], 'status': tmp[2], 'availability': tmp[3],
                                     'manager': tmp[4]}
                        leader_flag = True

                        if not ('Ready' in line and 'Active' in line):
                            node_status = 'nok'
                            fail_reason.append(tmp[1] + ' node is not ready.')
                    else:
                        node_json = {'hostname': tmp[1], 'status': tmp[2], 'availability': tmp[3],
                                     'manager': ''}

                    if 'Down' in line:
                        node_status = 'nok'
                        fail_reason.append(tmp[1] + ' node is down.')

                    node_list.append(node_json)

                if not leader_flag:
                    node_status = 'nok'
                    fail_reason.append('swarm leader node does not exist.')
            except:
                LOG.exception()
                node_status = 'nok'

        else:
            LOG.error("\'%s\' Swarm Node Check Error", node_ip)
            node_status = 'fail'

        try:
            sql = 'UPDATE ' + DB.SWARM_TBL + \
                  ' SET node = \"' + str(node_list) + '\"' + \
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE SWARM NODE INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] SWARM NODE DB Update Fail.')
        except:
            LOG.exception()

    except:
        LOG.exception()
        node_status = 'fail'

    return node_status, fail_reason


def swarm_service_check(conn, db_log, node_name, username, node_ip, swarm_manager):
    service_status = 'ok'
    service_list = []
    ps_list = []
    fail_reason = []

    try:
        cmd = 'ssh root@' + swarm_manager + ' \"sudo docker service ls\"'
        service_rt = SshCommand.ssh_exec(username, node_ip, cmd)

        instance_list = get_service_list()

        if service_rt is not None:
            try:
                for svc in instance_list:
                    find_flag = False
                    for line in service_rt.splitlines():
                        line = line.decode('utf-8')

                        if line.startswith('ID'):
                            continue

                        id, name, mode, rep, img = line.split()

                        if svc == name:
                            find_flag = True
                            rep_tmp = rep.split('/')

                            if not (rep_tmp[0] == rep_tmp[1]):
                                service_status = 'nok'
                                svc_json = {'name': name, 'mode': mode, 'replicas': rep, 'image': img,
                                            'status': 'nok', 'monitor_item': True}
                                fail_reason.append(svc_json)
                            else:
                                svc_json = {'name': name, 'mode': mode, 'replicas': rep, 'image': img,
                                            'status': 'ok', 'monitor_item': True}

                            service_list.append(svc_json)

                    if not find_flag:
                        service_status = 'nok'
                        fail_reason.append('swarm ' + svc + ' service does not exist.')
                        break

                for line in service_rt.splitlines():
                    line = line.decode('utf-8')

                    if line.startswith('ID'):
                        continue

                    id, name, mode, rep, img = line.split()

                    if name in instance_list:
                        continue

                    rep_tmp = rep.split('/')

                    if not (rep_tmp[0] == rep_tmp[1]):
                        svc_json = {'name': name, 'mode': mode, 'replicas': rep, 'image': img,
                                    'status': 'nok', 'monitor_item': False}
                    else:
                        svc_json = {'name': name, 'mode': mode, 'replicas': rep, 'image': img,
                                    'status': 'ok', 'monitor_item': False}

                    service_list.append(svc_json)

            except:
                LOG.exception()
                service_status = 'fail'

        else:
            LOG.error("\'%s\' Swarm Service Check Error", node_ip)
            service_status = 'fail'

        for app in instance_list:
            cmd = 'ssh root@' + swarm_manager + ' \"sudo docker service ps ' + app + '\"'
            ps_rt = SshCommand.ssh_exec(username, node_ip, cmd)

            if ps_rt is not None:
                for line in ps_rt.splitlines():
                    line = line.decode('utf-8')

                    if line.startswith('ID'):
                        continue

                    line = " ".join(line.split())
                    tmp = line.split(' ')

                    ps_json = {'name': tmp[1], 'image': tmp[2], 'node': tmp[3], 'desired_state': tmp[4],
                                'current_state': tmp[5]}
                    ps_list.append(ps_json)

            else:
                LOG.error("\'%s\' Swarm PS Check Error", node_ip)

        try:
            sql = 'UPDATE ' + DB.SWARM_TBL + \
                  ' SET service = \"' + str(service_list) + '\",' + \
                  ' ps = \"' + str(ps_list) + '\"' + \
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE SWARM SERVICE/PS INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] SWARM SERVICE/PS DB Update Fail.')
        except:
            LOG.exception()

    except:
        LOG.exception()
        service_status = 'fail'

    return service_status, fail_reason
