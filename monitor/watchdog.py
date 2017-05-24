# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import sys
import resource
import cmd_proc
import requests
import json

from datetime import datetime
from subprocess import Popen
from subprocess import PIPE
from api.config import CONF
from api.sona_log import LOG
from api.watcherdb import DB
from api.sbapi import SshCommand

def periodic(conn):
    cur_info = {}
    LOG.info("Periodic checking...%s", str(CONF.watchdog()['check_system']))

    try:
        node_list = cmd_proc.get_node_list('all', 'nodename, ip_addr, username, type')

        if not node_list:
            LOG.info("Not Exist Node data ...")
            return
    except:
        LOG.exception()
        return

    # Read cur alarm status
    sql = 'SELECT nodename, item, grade FROM ' + DB.EVENT_TBL
    LOG.info(sql)
    cur_grade = conn.cursor().execute(sql).fetchall()

    for nodename, item, grade in cur_grade:
        if not cur_info.has_key(nodename):
            cur_info[nodename] = {}

        cur_info[nodename][item] = grade

    for node_name, node_ip, user_name, type in node_list:
        # check ping
        ping = net_check(node_ip)

        app = 'fail'
        cpu = '-1'
        mem = '-1'
        disk = '-1'
        of_status = 'fail'
        ovsdb_status = 'fail'
        cluster_status = 'fail'
        web_status = 'fail'

        if ping == 'ok':
            if type.upper() == 'ONOS':
                # check connection
                of_status, ovsdb_status, cluster_status = onos_conn_check(conn, node_name, node_ip)

                # check web
                web_status = onos_web_check(conn, node_name, node_ip)

            # check swarm (app/node)
            if type.upper() == 'SWARM':
                app = swarm_check(conn, node_name, user_name, node_ip)
            else:
                # check app
                app = check_app(conn, node_name, node_ip, user_name, type)

            # check resource
            cpu, mem, disk = check_resource(conn, node_name, user_name, node_ip)

        # occur event (rest)
        # 1. ping check
        LOG.info(node_name)
        LOG.info(str(cur_info[node_name]))
        if cur_info[node_name]['ping'] != ping:
            occur_event(conn, node_name, 'ping', cur_info[node_name]['ping'], ping)

        # 2. app check
        if type.upper() == 'ONOS':
            if cur_info[node_name]['app'] != app:
                if not is_monitor_item(type, 'app'):
                    app = '-'
                else:
                    occur_event(conn, node_name, 'app', cur_info[node_name]['app'], app)

        # 3. resource check (CPU/MEM/DISK)
        cpu_grade = 'fail'
        if CONF.alarm().has_key('cpu'):
            if not is_monitor_item(type, 'cpu'):
                cpu_grade = '-'
            else:
                cpu_grade = get_grade('cpu', cpu)
                if cur_info[node_name]['cpu'] != cpu_grade:
                    occur_event(conn, node_name, 'cpu', cur_info[node_name]['cpu'], cpu_grade)


        mem_grade = 'fail'
        if CONF.alarm().has_key('memory'):
            if not is_monitor_item(type, 'memory'):
                mem_grade = '-'
            else:
                mem_grade = get_grade('memory', mem)
                if cur_info[node_name]['memory'] != mem_grade:
                    occur_event(conn, node_name, 'memory', cur_info[node_name]['memory'], mem_grade)

        disk_grade = 'fail'
        if CONF.alarm().has_key('disk'):
            if not is_monitor_item(type, 'disk'):
                disk_grade = '-'
            else:
                disk_grade = get_grade('disk', disk)
                if cur_info[node_name]['disk'] != disk_grade:
                    occur_event(conn, node_name, 'disk', cur_info[node_name]['disk'], disk_grade)

        # 4. Connection check (ovsdb, of, cluster) (ONOS)
        # 5. Web check (ONOS)
        if type.upper() == 'ONOS':
            if not is_monitor_item(type, 'ovsdb'):
                ovsdb_status = '-'
            elif cur_info[node_name]['ovsdb'] != ovsdb_status:
                occur_event(conn, node_name, 'ovsdb', cur_info[node_name]['ovsdb'], ovsdb_status)

            if not is_monitor_item(type, 'of'):
                of_status = '-'
            elif cur_info[node_name]['of'] != of_status:
                occur_event(conn, node_name, 'of', cur_info[node_name]['of'], of_status)

            if not is_monitor_item(type, 'cluster'):
                cluster_status = '-'
            elif cur_info[node_name]['cluster'] != cluster_status:
                occur_event(conn, node_name, 'cluster', cur_info[node_name]['cluster'], cluster_status)

            if not is_monitor_item(type, 'web'):
                web_status = '-'
            elif cur_info[node_name]['web'] != web_status:
                occur_event(conn, node_name, 'web', cur_info[node_name]['web'], web_status)

        try:
            sql = 'UPDATE ' + DB.STATUS_TBL + \
                  ' SET cpu = \'' + cpu_grade + '\',' + \
                  ' memory = \'' + mem_grade + '\',' + \
                  ' disk = \'' + disk_grade + '\',' + \
                  ' ping = \'' + ping + '\',' + \
                  ' app = \'' + app + '\',' + \
                  ' web = \'' + web_status + '\',' + \
                  ' ovsdb = \'' + ovsdb_status + '\',' + \
                  ' of = \'' + of_status + '\',' + \
                  ' cluster = \'' + cluster_status + '\',' + \
                  ' time = \'' + str(datetime.now()) + '\'' + \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update Status info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('DB Update Fail.')
        except:
            LOG.exception()

def get_grade(item, value):
    critical, major, minor = (CONF.alarm()[item])

    if value == '-1':
        return 'fail'

    if float(value) >= float(critical):
        return 'critical'
    elif float(value) >= float(major):
        return 'major'
    elif float(value) >= float(minor):
        return 'minor'

    return 'normal'

def occur_event(conn, node_name, item, pre_value, cur_value):
    time = str(datetime.now())
    desc = pre_value + ' -> ' + cur_value
    sql = 'UPDATE ' + DB.EVENT_TBL + \
          ' SET grade = \'' + cur_value + '\'' + ',' + \
          ' desc = \'' + desc + '\'' + ',' + \
          ' time = \'' + time + '\'' + \
          ' WHERE nodename = \'' + node_name + '\' and item = \'' + item + '\''
    LOG.info('Update alarm info = ' + sql)

    if DB.sql_execute(sql, conn) != 'SUCCESS':
        LOG.error('DB Update Fail.')

    push_event(node_name, item, cur_value, desc, time)

def push_event(node_name, item, grade, desc, time):
    sql = 'SELECT * FROM ' + DB.REGI_SYS_TBL

    with DB.connection() as conn:
        url_list = conn.cursor().execute(sql).fetchall()

    conn.close()

    for url, auth in url_list:
        header = {'Content-Type': 'application/json', 'Authorization': auth}
        req_body = {'event': 'occur', 'system': node_name, 'item': item, 'grade': grade, 'desc': desc, 'time': time}
        req_body_json = json.dumps(req_body)

        try:
            requests.post(url, headers=header, data=req_body_json, timeout = 2)
        except:
            # Push event does not respond
            pass


def net_check(node):
    if CONF.watchdog()['method'] == 'ping':
        timeout = CONF.watchdog()['timeout']
        if sys.platform == 'darwin':
            timeout = timeout * 1000

        cmd = 'ping -c1 -W%d -n %s' % (timeout, node)

        result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, error = result.communicate()

        if result.returncode != 0:
            LOG.error("\'%s\' Network Check Error(%d) ", node, result.returncode)
            return 'nok'
        else:
            return 'ok'

def check_app(conn, node_name, node_ip, user_name, type):
    app = 'nok'

    if type.upper() == 'ONOS':
        app, app_list = onos_app_check(node_ip)

        try:
            sql = 'UPDATE ' + DB.ONOS_TBL + \
                  ' SET applist = \'' + app_list + '\'' \
                                                   ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update app info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('DB Update Fail.')
        except:
            LOG.exception()

    elif type.upper() == 'XOS':
        app = xos_app_check(node_ip)
    elif type.upper() == 'OPENSTACK':
        app = openstack_app_check(node_ip)

    return app

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

def check_resource(conn, node_name, user_name, node_ip):
    try:
        cpu = str(resource.get_cpu_usage(user_name, node_ip, True))
        mem = str(resource.get_mem_usage(user_name, node_ip, True))
        disk = str(resource.get_disk_usage(user_name, node_ip, True))

        try:
            sql = 'UPDATE ' + DB.RESOURCE_TBL + \
                  ' SET cpu = \'' + cpu + '\',' + \
                  ' memory = \'' + mem + '\',' + \
                  ' disk = \'' + disk + '\'' \
                                        ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update Resource info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('DB Update Fail.')
        except:
            LOG.exception()

        return cpu, mem, disk
    except:
        LOG.exception()
        return -1, -1, -1

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

# TODO xos app check
def xos_app_check(node):
    return 'nok'


# TODO swarm app check
def swarm_check(conn, node_name, user_name, node_ip):
    str_node = ''
    str_service = ''
    str_ps = ''

    ret_app = 'ok'

    node_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo docker node ls')

    if node_rt is not None:
        for line in node_rt.splitlines():
            line = line.decode('utf-8')
            str_node = str_node + line + '\n'
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
            ret_app = 'nok'

        for line in service_rt.splitlines():
            line = line.decode('utf-8')
            str_service = str_service + line + '\n'
    else:
        LOG.error("\'%s\' Swarm Service Check Error", node_ip)
        str_service = 'fail'
        ret_app = 'nok'

    ps_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo docker service ps my_web')

    if ps_rt is not None:
        for line in ps_rt.splitlines():
            line = line.decode('utf-8')
            str_ps = str_ps + line + '\n'
    else:
        LOG.error("\'%s\' Swarm PS Check Error", node_ip)
        str_ps = 'fail'

    try:
        LOG.info(DB.STATUS_TBL)
        LOG.info(str_node)
        LOG.info(str_service)
        LOG.info(str_ps)
        LOG.info(node_name)
        sql = 'UPDATE ' + DB.SWARM_TBL + \
              ' SET node = \'' + str_node + '\',' + \
              ' service = \'' + str_service + '\',' + \
              ' ps = \'' + str_ps + '\'' + \
              ' WHERE nodename = \'' + node_name + '\''
        LOG.info('Update Swarm info = ' + sql)

        if DB.sql_execute(sql, conn) != 'SUCCESS':
            LOG.error('DB Update Fail.')

        return ret_app
    except:
        LOG.exception()
        return 'nok'


# TODO openstack app check
def openstack_app_check(node):
    return 'nok'

def is_monitor_item(node_type, item_type):
    conf_dict = CONF_MAP[node_type.upper()]()

    if conf_dict.has_key('alarm_off_list'):
        for item in (CONF_MAP[node_type.upper()]())['alarm_off_list']:

            if ':' + item_type in item:
                return False

    return True

CONF_MAP = {'ONOS': CONF.onos,
            'XOS': CONF.xos,
            'SWARM': CONF.swarm,
            'OPENSTACK': CONF.openstack}
