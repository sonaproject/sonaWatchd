# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import sys
import alarm_event
import chk_onos
import chk_swarm
import chk_openstack
import chk_resource
import cmd_proc

from datetime import datetime
from subprocess import Popen
from subprocess import PIPE
from api.config import CONF
from api.sona_log import LOG
from api.watcherdb import DB


def periodic(conn):
    try:
        cur_info = {}
        LOG.info("Periodic checking...%s", str(CONF.watchdog()['check_system']))

        try:
            node_list = cmd_proc.get_node_list('all', 'nodename, ip_addr, username, type, sub_type')

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

        # check GW ratio
        gw_total = 0

        # check node traffic
        rx_total = 0
        tx_total = 0

        openstack_rx_dic = dict()
        openstack_tx_dic = dict()
        rx_tx_err_info = dict()
        patch_tx_dic = dict()
        for node_name, node_ip, user_name, type, sub_type in node_list:
            if type.upper() == 'OPENSTACK':
                openstack_rx_dic[node_name], openstack_tx_dic[node_name], rx_tx_err_info[node_name], patch_tx_dic[node_name] = chk_openstack.rx_tx_check(user_name, node_ip)

                if openstack_rx_dic[node_name] > 0:
                    rx_total = rx_total + openstack_rx_dic[node_name]

                if openstack_tx_dic[node_name] > 0:
                    tx_total = tx_total + openstack_tx_dic[node_name]

                if sub_type == 'GATEWAY':
                    if openstack_rx_dic[node_name] > 0:
                        gw_total = gw_total + openstack_rx_dic[node_name]

        # calc node traffic rate
        node_ratio  = chk_openstack.calc_node_traffic_ratio(rx_total, tx_total)

        for node_name, node_ip, user_name, type, sub_type in node_list:
            # check ping
            network = net_check(node_ip)

            cpu = '-1'
            memory = '-1'
            disk = '-1'

            onos_app = 'fail'
            onos_rest = 'fail'

            v_router = 'fail'

            swarm_node = 'fail'
            swarm_svc = 'fail'

            onos_ha_list = 'fail'
            onos_ha_ratio = 'fail'

            openstack_node = 'fail'

            onos_of = 'fail'
            onos_ovsdb = 'fail'
            onos_cluster = 'fail'

            traffic_gw = 'fail'
            traffic_node = 'fail'
            traffic_controller = 'fail'
            traffic_internal = 'fail'

            if network == 'ok':
                if type.upper() == 'ONOS':
                    # check node
                    openstack_node = chk_onos.onos_node_check(conn, node_name, node_ip)

                    # check app
                    onos_app = check_app(conn, node_name, node_ip, user_name, type)

                    # check connection
                    onos_of, onos_ovsdb, onos_cluster = chk_onos.onos_conn_check(conn, node_name, node_ip)

                    # check web
                    onos_rest = chk_onos.onos_web_check(conn, node_name, node_ip)

                    onos_ha_list, onos_ha_ratio = chk_onos.get_ha_stats(conn, ha_dic, node_name)

                    # check controller traffic
                    traffic_controller = chk_onos.controller_traffic_check(conn, node_name, node_ip)

                # check swarm (app/node)
                elif type.upper() == 'SWARM':
                    swarm_svc, swarm_node = chk_swarm.swarm_check(conn, node_name, user_name, node_ip)
                # check vrouter, gw_ratio
                elif type.upper() == 'OPENSTACK':
                    traffic_node = chk_openstack.get_node_traffic(conn, node_name, node_ratio, openstack_rx_dic,
                                                                  openstack_tx_dic, rx_total, tx_total, rx_tx_err_info[node_name])
                    traffic_internal = chk_openstack.get_internal_traffic(conn, node_name, node_ip, user_name, sub_type,
                                                                          openstack_rx_dic[node_name], patch_tx_dic[node_name])
                    if sub_type.upper() == 'GATEWAY':
                        v_router = chk_openstack.vrouter_check(conn, node_name, user_name, node_ip)
                        traffic_gw = chk_openstack.get_gw_ratio(conn, node_name, node_ip, openstack_rx_dic[node_name], gw_total)

                else:
                    # check app
                    onos_app = check_app(conn, node_name, node_ip, user_name, type)

                # check resource
                cpu, memory, disk = chk_resource.check_resource(conn, node_name, user_name, node_ip)

            # occur event (rest)
            # 1. ping check
            LOG.info(node_name)
            LOG.info(str(cur_info[node_name]))

            network = alarm_event.process_event(conn, node_name, type, 'NETWORK', cur_info[node_name]['NETWORK'], network)

            # 3. resource check (CPU/MEM/DISK)
            cpu_grade = 'fail'
            if CONF.alarm().has_key('cpu'):
                if not alarm_event.is_monitor_item(type, 'CPU'):
                    cpu_grade = '-'
                else:
                    cpu_grade = alarm_event.get_grade('cpu', cpu)
                    if cur_info[node_name]['CPU'] != cpu_grade:
                        alarm_event.occur_event(conn, node_name, 'CPU', cur_info[node_name]['CPU'], cpu_grade)


            mem_grade = 'fail'
            if CONF.alarm().has_key('memory'):
                if not alarm_event.is_monitor_item(type, 'MEMORY'):
                    mem_grade = '-'
                else:
                    mem_grade = alarm_event.get_grade('memory', memory)
                    if cur_info[node_name]['MEMORY'] != mem_grade:
                        alarm_event.occur_event(conn, node_name, 'MEMORY', cur_info[node_name]['MEMORY'], mem_grade)

            disk_grade = 'fail'
            if CONF.alarm().has_key('disk'):
                if not alarm_event.is_monitor_item(type, 'DISK'):
                    disk_grade = '-'
                else:
                    disk_grade = alarm_event.get_grade('disk', disk)
                    if cur_info[node_name]['DISK'] != disk_grade:
                        alarm_event.occur_event(conn, node_name, 'DISK', cur_info[node_name]['DISK'], disk_grade)

            # 2. app check
            # 4. Connection check (ovsdb, of, cluster) (ONOS)
            # 5. Web check (ONOS)
            # 8. HA Status (ONOS)
            # 9. Node check (ONOS)
            if type.upper() == 'ONOS':
                onos_app = alarm_event.process_event(conn, node_name, type, 'ONOS_APP', cur_info[node_name]['ONOS_APP'], onos_app)
                onos_ovsdb = alarm_event.process_event(conn, node_name, type, 'ONOS_OVSDB', cur_info[node_name]['ONOS_OVSDB'], onos_ovsdb)
                onos_of = alarm_event.process_event(conn, node_name, type, 'ONOS_OF', cur_info[node_name]['ONOS_OF'], onos_of)
                onos_cluster = alarm_event.process_event(conn, node_name, type, 'ONOS_CLUSTER', cur_info[node_name]['ONOS_CLUSTER'], onos_cluster)
                onos_rest = alarm_event.process_event(conn, node_name, type, 'ONOS_REST', cur_info[node_name]['ONOS_REST'], onos_rest)
                onos_ha_list = alarm_event.process_event(conn, node_name, type, 'ONOS_HA_LIST', cur_info[node_name]['ONOS_HA_LIST'], onos_ha_list)
                onos_ha_ratio = alarm_event.process_event(conn, node_name, type, 'ONOS_HA_RATIO', cur_info[node_name]['ONOS_HA_RATIO'], onos_ha_ratio)
                openstack_node = alarm_event.process_event(conn, node_name, type, 'OPENSTACK_NODE', cur_info[node_name]['OPENSTACK_NODE'], openstack_node)
                traffic_controller = alarm_event.process_event(conn, node_name, type, 'TRAFFIC_CONTROLLER', cur_info[node_name]['TRAFFIC_CONTROLLER'], traffic_controller)

            # 6. Swarm Check
            elif type.upper() == 'SWARM':
                # 2. app check
                swarm_svc = alarm_event.process_event(conn, node_name, type, 'SWARM_SVC', cur_info[node_name]['SWARM_SVC'], swarm_svc)
                swarm_node = alarm_event.process_event(conn, node_name, type, 'SWARM_NODE', cur_info[node_name]['SWARM_NODE'], swarm_node)

            # 7. Vrouter Check
            elif type.upper() == 'OPENSTACK':
                traffic_internal = alarm_event.process_event(conn, node_name, type, 'TRAFFIC_INTERNAL',
                                                             cur_info[node_name]['TRAFFIC_INTERNAL'], traffic_internal)
                if sub_type.upper() == 'GATEWAY':
                    v_router = alarm_event.process_event(conn, node_name, type, 'VROUTER', cur_info[node_name]['VROUTER'], v_router)
                    traffic_gw = alarm_event.process_event(conn, node_name, type, 'TRAFFIC_GW', cur_info[node_name]['TRAFFIC_GW'], traffic_gw)
                elif sub_type.upper() == 'COMPUTE':
                    v_router = '-'
                    traffic_gw = '-'

                traffic_node = alarm_event.process_event(conn, node_name, type, 'TRAFFIC_NODE', cur_info[node_name]['TRAFFIC_NODE'], traffic_node)

            try:
                sql = 'UPDATE ' + DB.STATUS_TBL + \
                      ' SET CPU = \'' + cpu_grade + '\',' + \
                      ' MEMORY = \'' + mem_grade + '\',' + \
                      ' DISK = \'' + disk_grade + '\',' + \
                      ' NETWORK = \'' + network + '\',' + \
                      ' ONOS_APP = \'' + onos_app + '\',' + \
                      ' ONOS_REST = \'' + onos_rest + '\',' + \
                      ' ONOS_OVSDB = \'' + onos_ovsdb + '\',' + \
                      ' ONOS_OF = \'' + onos_of + '\',' + \
                      ' ONOS_CLUSTER = \'' + onos_cluster + '\',' + \
                      ' SWARM_NODE = \'' + swarm_node + '\',' + \
                      ' OPENSTACK_NODE = \'' + openstack_node + '\',' + \
                      ' SWARM_SVC = \'' + swarm_svc + '\',' + \
                      ' VROUTER = \'' + v_router + '\',' + \
                      ' ONOS_HA_LIST = \'' + onos_ha_list + '\',' + \
                      ' ONOS_HA_RATIO = \'' + onos_ha_ratio + '\',' + \
                      ' TRAFFIC_GW = \'' + traffic_gw + '\',' + \
                      ' TRAFFIC_NODE = \'' + traffic_node + '\',' + \
                      ' TRAFFIC_CONTROLLER = \'' + traffic_controller + '\',' + \
                      ' TRAFFIC_INTERNAL = \'' + traffic_internal + '\',' + \
                      ' time = \'' + str(datetime.now()) + '\'' + \
                      ' WHERE nodename = \'' + node_name + '\''
                LOG.info('Update Status info = ' + sql)

                if DB.sql_execute(sql, conn) != 'SUCCESS':
                    LOG.error('DB Update Fail.')
            except:
                LOG.exception()
    except:
        LOG.exception()

def net_check(node):
    try:
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
    except:
        LOG.exception()


def check_app(conn, node_name, node_ip, user_name, type):
    try:
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
    except:
        LOG.exception()
        return 'fail'


# TODO xos app check
def xos_app_check(node):
    return 'nok'


# TODO openstack app check
def openstack_app_check(node):
    return 'nok'

