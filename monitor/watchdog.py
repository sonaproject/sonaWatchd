# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import sys
import resource
import cmd_proc
import requests
import base64
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
        node_list = cmd_proc.get_node_list('all', 'nodename, ip_addr, username')

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

    for node_name, node_ip, user_name in node_list:
        ping = net_check(node_ip)
        app = ''
        cpu = ''
        mem = ''
        disk = ''

        if ping == 'ok':
            if node_ip in str(CONF.onos()['list']):
                app = onos_app_check(node_ip)
            elif node_ip in str(CONF.xos()['list']):
                app = xos_app_check(node_ip)
            elif node_ip in str(CONF.swarm()['list']):
                app = swarm_app_check(node_ip)
            elif node_ip in str(CONF.openstack()['list']):
                app = openstack_app_check(node_ip)

            cpu = str(resource.get_cpu_usage(user_name, node_ip, True))
            mem = str(resource.get_mem_usage(user_name, node_ip, True))
            disk = str(resource.get_disk_usage(user_name, node_ip, True))
        else:
            app = 'nok'
            cpu = '-1'
            mem = '-1'
            disk = '-1'

        try:
            sql = 'UPDATE ' + DB.STATUS_TBL + \
                  ' SET cpu = ' + cpu + ',' + \
                  ' memory = ' + mem + ',' + \
                  ' disk = ' + disk + ',' + \
                  ' ping = \'' + ping + '\'' + ',' + \
                  ' app = \'' + app + '\'' + ',' + \
                  ' time = \'' + str(datetime.now()) + '\'' + \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update Status info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('DB Update Fail.')
        except:
            LOG.exception()

        # occur event (rest)
        # 1. ping check
        if cur_info[node_name]['ping'] != ping:
            occur_event(conn, node_name, 'ping', cur_info[node_name]['ping'], ping)

        # 2. app check
        if cur_info[node_name]['app'] != app:
            occur_event(conn, node_name, 'app', cur_info[node_name]['app'], app)

        # 3. resource check (CPU/MEM/DISK)
        if CONF.alarm().has_key('cpu'):
            grade = get_grade('cpu', cpu)
            if cur_info[node_name]['cpu'] != grade:
                occur_event(conn, node_name, 'cpu', cur_info[node_name]['cpu'], grade)

        if CONF.alarm().has_key('memory'):
            grade = get_grade('memory', mem)
            if cur_info[node_name]['memory'] != grade:
                occur_event(conn, node_name, 'memory', cur_info[node_name]['memory'], grade)

        if CONF.alarm().has_key('disk'):
            grade = get_grade('disk', disk)
            if cur_info[node_name]['disk'] != grade:
                occur_event(conn, node_name, 'disk', cur_info[node_name]['disk'], grade)

def get_grade(item, value):
    critical, major, minor = (CONF.alarm()[item])

    if value >= critical:
        return 'critical'
    elif value >= major:
        return 'major'
    elif value >= minor:
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

    # if default->ok or normal, skip
    if not (pre_value == 'none' and cur_value in ['ok', 'normal']):
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
            # rest timeout
            LOG.exception()


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


def onos_app_check(node):

    app_rt = SshCommand.onos_ssh_exec(node, 'apps -a -s')

    app_active_list = list()
    if app_rt is not None:
        for line in app_rt.splitlines():
            app_active_list.append(line.split(".")[2].split()[0])
        if set(CONF.onos()['app_list']).issubset(app_active_list):
            return 'ok'
        else:
            LOG.error("\'%s\' Application Check Error", node)
            return 'nok'
    else:
        LOG.error("\'%s\' Application Check Error", node)
        return 'nok'


# TODO xos app check
def xos_app_check(node):
    return 'nok'


# TODO swarm app check
def swarm_app_check(node):
    return 'nok'


# TODO openstack app check
def openstack_app_check(node):
    return 'nok'


