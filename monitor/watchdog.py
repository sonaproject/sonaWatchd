# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import sys
import alarm_event
import chk_onos
import chk_swarm
import chk_vrouter
import chk_resource
import cmd_proc

from datetime import datetime
from subprocess import Popen
from subprocess import PIPE
from api.config import CONF
from api.sona_log import LOG
from api.watcherdb import DB


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

    # check HA, once
    ha_dic = chk_onos.onos_ha_check(conn)

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
        node = 'fail'
        v_router = 'fail'
        ha_stats = 'fail'

        if ping == 'ok':
            if type.upper() == 'ONOS':
                # check connection
                of_status, ovsdb_status, cluster_status = chk_onos.onos_conn_check(conn, node_name, node_ip)

                # check web
                web_status = chk_onos.onos_web_check(conn, node_name, node_ip)

                ha_stats = chk_onos.get_ha_stats(ha_dic, node_name)

            # check swarm (app/node)
            if type.upper() == 'SWARM':
                app, node = chk_swarm.swarm_check(conn, node_name, user_name, node_ip)
            # check vrouter
            elif type.upper() == 'OPENSTACK':
                v_router = chk_vrouter.vrouter_check(conn, node_name, user_name, node_ip)
            else:
                # check app
                app = check_app(conn, node_name, node_ip, user_name, type)

            # check resource
            cpu, mem, disk = chk_resource.check_resource(conn, node_name, user_name, node_ip)

        # occur event (rest)
        # 1. ping check
        LOG.info(node_name)
        LOG.info(str(cur_info[node_name]))
        if cur_info[node_name]['ping'] != ping:
            alarm_event.occur_event(conn, node_name, 'ping', cur_info[node_name]['ping'], ping)

        # 2. app check
        if cur_info[node_name]['app'] != app:
            if not alarm_event.is_monitor_item(type, 'app'):
                app = '-'
            else:
                alarm_event.occur_event(conn, node_name, 'app', cur_info[node_name]['app'], app)

        # 3. resource check (CPU/MEM/DISK)
        cpu_grade = 'fail'
        if CONF.alarm().has_key('cpu'):
            if not alarm_event.is_monitor_item(type, 'cpu'):
                cpu_grade = '-'
            else:
                cpu_grade = alarm_event.get_grade('cpu', cpu)
                if cur_info[node_name]['cpu'] != cpu_grade:
                    alarm_event.occur_event(conn, node_name, 'cpu', cur_info[node_name]['cpu'], cpu_grade)


        mem_grade = 'fail'
        if CONF.alarm().has_key('memory'):
            if not alarm_event.is_monitor_item(type, 'memory'):
                mem_grade = '-'
            else:
                mem_grade = alarm_event.get_grade('memory', mem)
                if cur_info[node_name]['memory'] != mem_grade:
                    alarm_event.occur_event(conn, node_name, 'memory', cur_info[node_name]['memory'], mem_grade)

        disk_grade = 'fail'
        if CONF.alarm().has_key('disk'):
            if not alarm_event.is_monitor_item(type, 'disk'):
                disk_grade = '-'
            else:
                disk_grade = alarm_event.get_grade('disk', disk)
                if cur_info[node_name]['disk'] != disk_grade:
                    alarm_event.occur_event(conn, node_name, 'disk', cur_info[node_name]['disk'], disk_grade)

        # 4. Connection check (ovsdb, of, cluster) (ONOS)
        # 5. Web check (ONOS)
        # 8. HA Status (ONOS)
        if type.upper() == 'ONOS':
            if not alarm_event.is_monitor_item(type, 'ovsdb'):
                ovsdb_status = '-'
            elif cur_info[node_name]['ovsdb'] != ovsdb_status:
                alarm_event.occur_event(conn, node_name, 'ovsdb', cur_info[node_name]['ovsdb'], ovsdb_status)

            if not alarm_event.is_monitor_item(type, 'of'):
                of_status = '-'
            elif cur_info[node_name]['of'] != of_status:
                alarm_event.occur_event(conn, node_name, 'of', cur_info[node_name]['of'], of_status)

            if not alarm_event.is_monitor_item(type, 'cluster'):
                cluster_status = '-'
            elif cur_info[node_name]['cluster'] != cluster_status:
                alarm_event.occur_event(conn, node_name, 'cluster', cur_info[node_name]['cluster'], cluster_status)

            if not alarm_event.is_monitor_item(type, 'web'):
                web_status = '-'
            elif cur_info[node_name]['web'] != web_status:
                alarm_event.occur_event(conn, node_name, 'web', cur_info[node_name]['web'], web_status)

            if not alarm_event.is_monitor_item(type, 'ha_stats'):
                ha_stats = '-'
            elif cur_info[node_name]['ha_stats'] != ha_stats:
                alarm_event.occur_event(conn, node_name, 'ha_stats', cur_info[node_name]['ha_stats'], ha_stats)

        # 6. Swarm Check
        elif type.upper() == 'SWARM':
            if not alarm_event.is_monitor_item(type, 'node'):
                node = '-'
            elif cur_info[node_name]['node'] != node:
                alarm_event.occur_event(conn, node_name, 'node', cur_info[node_name]['node'], node)

        # 7. Vrouter Check
        elif type.upper() == 'OPENSTACK':
            if not alarm_event.is_monitor_item(type, 'vrouter'):
                v_router = '-'
            elif cur_info[node_name]['vrouter'] != v_router:
                alarm_event.occur_event(conn, node_name, 'vrouter', cur_info[node_name]['vrouter'], v_router)

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
                  ' node = \'' + node + '\',' + \
                  ' vrouter = \'' + v_router + '\',' + \
                  ' ha_stats = \'' + ha_stats + '\',' + \
                  ' time = \'' + str(datetime.now()) + '\'' + \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update Status info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('DB Update Fail.')
        except:
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


def check_app(conn, node_name, node_ip, user_name, type):
    app = 'nok'

    if type.upper() == 'ONOS':
        app, app_list = chk_onos.onos_app_check(node_ip)

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


# TODO xos app check
def xos_app_check(node):
    return 'nok'


# TODO openstack app check
def openstack_app_check(node):
    return 'nok'

