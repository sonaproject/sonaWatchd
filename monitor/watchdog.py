# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import sys
import alarm_event
import chk_onos
import chk_xos
import chk_swarm
import chk_openstack
import chk_resource
import chk_ha
import cmd_proc

from datetime import datetime
from subprocess import Popen
from subprocess import PIPE
from api.config import CONF
from api.sona_log import LOG
from api.watcherdb import DB


def periodic(conn, pre_stat, db_log):
    try:
        cur_info = {}
        LOG.info('Periodic checking %s', str(CONF.watchdog()['check_system']))

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

        db_log.write_log(sql)
        cur_grade = conn.cursor().execute(sql).fetchall()

        for nodename, item, grade in cur_grade:
            if not cur_info.has_key(nodename):
                cur_info[nodename] = {}

            cur_info[nodename][item] = grade

        # check HA, once
        if 'HA' in CONF.watchdog()['check_system']:
            ha_dic = chk_ha.onos_ha_check(conn, db_log)
            global_ha_svc, global_ha_ratio, global_svc_reason, global_ha_ratio_reason = chk_ha.get_ha_stats(ha_dic)

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

        for node_name, node_ip, user_name, type, sub_type in node_list:
            LOG.info('------------------------------------ ' + node_name + ' START ------------------------------------')

            cpu = '-1'
            memory = '-1'
            disk = '-1'

            onos_app = 'fail'
            onos_rest = 'fail'

            v_router = 'fail'

            xos_status = 'fail'
            synchronizer_status = 'fail'

            swarm_node = 'fail'
            swarm_svc = 'fail'

            ha_svc = 'fail'
            ha_ratio = 'fail'

            openstack_node = 'fail'

            onos_of = 'fail'
            onos_cluster = 'fail'

            traffic_gw = 'fail'
            port_stat_vxlan = 'fail'
            traffic_controller = 'fail'
            traffic_internal = 'fail'

            # check ping
            network = net_check(node_ip)

            # occur event (rest)
            # 1. ping check
            reason = []
            if network == 'nok':
                reason.append('ping transmit failed')

            network = alarm_event.process_event(conn, db_log, node_name, type, 'NETWORK', cur_info[node_name]['NETWORK'], network, reason)

            if network == 'ok':
                if type.upper() == 'ONOS':
                    # check node
                    openstack_node, reason = chk_onos.onos_node_check(conn, db_log, node_name, node_ip)
                    openstack_node = alarm_event.process_event(conn, db_log, node_name, type, 'OPENSTACK_NODE',
                                                               cur_info[node_name]['OPENSTACK_NODE'], openstack_node, reason)
                    LOG.info('[' + node_name + '][OPENSTACK_NODE][' + openstack_node + ']' + str(reason))

                    # check app
                    onos_app, reason = chk_onos.onos_app_check(conn, db_log, node_name, node_ip)
                    onos_app = alarm_event.process_event(conn, db_log, node_name, type, 'ONOS_APP',
                                                         cur_info[node_name]['ONOS_APP'], onos_app, reason)
                    LOG.info('[' + node_name + '][ONOS_APP][' + onos_app + ']' + str(reason))

                    # check connection
                    onos_of, onos_cluster, of_reason, cluster_reason = chk_onos.onos_conn_check(conn, db_log, node_name, node_ip)
                    onos_of = alarm_event.process_event(conn, db_log, node_name, type, 'ONOS_OPENFLOW',
                                                        cur_info[node_name]['ONOS_OPENFLOW'], onos_of, of_reason)
                    onos_cluster = alarm_event.process_event(conn, db_log, node_name, type, 'ONOS_CLUSTER',
                                                             cur_info[node_name]['ONOS_CLUSTER'], onos_cluster, cluster_reason)
                    LOG.info('[' + node_name + '][ONOS_OPENFLOW][' + onos_of + ']' + str(of_reason))
                    LOG.info('[' + node_name + '][ONOS_CLUSTER][' + onos_cluster + ']' + str(cluster_reason))

                    # check web
                    onos_rest, reason = chk_onos.onos_rest_check(conn, db_log, node_name, node_ip)
                    onos_rest = alarm_event.process_event(conn, db_log, node_name, type, 'ONOS_REST',
                                                          cur_info[node_name]['ONOS_REST'], onos_rest, reason)
                    LOG.info('[' + node_name + '][ONOS_REST][' + onos_rest + ']' + str(reason))

                    # check controller traffic
                    traffic_controller, pre_stat, reason = chk_onos.controller_traffic_check(conn, db_log, node_name, node_ip, pre_stat)
                    traffic_controller = alarm_event.process_event(conn, db_log, node_name, type, 'TRAFFIC_CONTROLLER',
                                                                   cur_info[node_name]['TRAFFIC_CONTROLLER'],
                                                                   traffic_controller, reason)
                    LOG.info('[' + node_name + '][ONOS_TRAFFIC_CONTROLLER][' + traffic_controller + ']' + str(reason))

                elif type.upper() == 'HA':
                    ha_svc = global_ha_svc
                    ha_svc = alarm_event.process_event(conn, db_log, node_name, type, 'HA_SVC', cur_info[node_name]['HA_SVC'],
                                                       ha_svc, global_svc_reason)
                    LOG.info('[' + node_name + '][HA_SVC][' + ha_svc + ']' + str(global_svc_reason))

                    ha_ratio = global_ha_ratio
                    ha_ratio = alarm_event.process_event(conn, db_log, node_name, type, 'HA_RATIO', cur_info[node_name]['HA_RATIO'],
                                                         ha_ratio, global_ha_ratio_reason)
                    LOG.info('[' + node_name + '][HA_RATIO][' + ha_ratio + ']' + str(global_ha_ratio_reason))

                # check xos (status/synchronizer)
                elif type.upper() == 'XOS':
                    xos_status, reason = chk_xos.xos_status_check(conn, db_log, node_name)

                    xos_status = alarm_event.process_event(conn, db_log, node_name, type, 'XOS_SVC',
                                                      cur_info[node_name]['XOS_SVC'], xos_status, reason)

                    LOG.info('[' + node_name + '][XOS_SVC][' + xos_status + ']' + str(reason))

                    synchronizer_status, reason = chk_xos.xos_sync_check(conn, db_log, node_name)

                    synchronizer_status = alarm_event.process_event(conn, db_log, node_name, type, 'SYNCHRONIZER',
                                                           cur_info[node_name]['SYNCHRONIZER'], synchronizer_status, reason)

                    LOG.info('[' + node_name + '][SYNCHRONIZER][' + synchronizer_status + ']' + str(reason))

                    # check swarm (app/node)
                    swarm_node, reason = chk_swarm.swarm_node_check(conn, db_log, node_name, user_name, node_ip)
                    swarm_node = alarm_event.process_event(conn, db_log, node_name, type, 'SWARM_NODE',
                    cur_info[node_name]['SWARM_NODE'], swarm_node, reason)

                    LOG.info('[' + node_name + '][SWARM_NODE][' + swarm_node + ']' + str(reason))

                    # add reason
                    #reason = []
                    #swarm_svc = alarm_event.process_event(conn, db_log, node_name, type, 'SWARM_SVC',
                                                          #cur_info[node_name]['SWARM_SVC'], swarm_svc, reason)

                # check vrouter, gw_ratio
                elif type.upper() == 'OPENSTACK':
                    port_stat_vxlan, pre_stat, reason = chk_openstack.get_node_traffic(conn, db_log, node_name, openstack_rx_dic,
                                                                  openstack_tx_dic, rx_total, tx_total, rx_tx_err_info[node_name], pre_stat)
                    port_stat_vxlan = alarm_event.process_event(conn, db_log, node_name, type, 'PORT_STAT_VXLAN',
                                                                cur_info[node_name]['PORT_STAT_VXLAN'], port_stat_vxlan, reason)
                    LOG.info('[' + node_name + '][PORT_STAT_VXLAN][' + port_stat_vxlan + ']' + str(reason))

                    traffic_internal, pre_stat, reason = chk_openstack.get_internal_traffic(conn, db_log, node_name, node_ip, user_name, sub_type,
                                                                          openstack_rx_dic[node_name], patch_tx_dic[node_name], pre_stat)
                    traffic_internal = alarm_event.process_event(conn, db_log, node_name, type, 'TRAFFIC_INTERNAL',
                                                                 cur_info[node_name]['TRAFFIC_INTERNAL'],
                                                                 traffic_internal, reason)
                    LOG.info('[' + node_name + '][TRAFFIC_INTERNAL][' + traffic_internal + ']' + str(reason))

                    if sub_type.upper() == 'GATEWAY':
                        v_router, reason = chk_openstack.vrouter_check(conn, db_log, node_name, user_name, node_ip)
                        v_router = alarm_event.process_event(conn, db_log, node_name, type, 'GATEWAY',
                                                             cur_info[node_name]['GATEWAY'], v_router, reason)
                        LOG.info('[' + node_name + '][GATEWAY][' + v_router + ']' + str(reason))

                        traffic_gw, pre_stat, reason = chk_openstack.get_gw_ratio_gateway(conn, db_log, node_ip, node_name, openstack_rx_dic[node_name], gw_total, pre_stat)

                    elif sub_type.upper() == 'COMPUTE':
                        v_router = '-'
                        traffic_gw, pre_stat, reason = chk_openstack.get_gw_ratio_compute(conn, db_log, node_ip, node_name, pre_stat)

                    traffic_gw = alarm_event.process_event(conn, db_log, node_name, type, 'TRAFFIC_GW',
                                                           cur_info[node_name]['TRAFFIC_GW'], traffic_gw, reason)
                    LOG.info('[' + node_name + '][TRAFFIC_GW][' + traffic_gw + ']' + str(reason))

                # check resource
                cpu, memory, disk = chk_resource.check_resource(conn, db_log, node_name, user_name, node_ip)

            reason = []
            # 3. resource check (CPU/MEM/DISK)
            cpu_grade = 'fail'
            if CONF.alarm().has_key('cpu'):
                if not alarm_event.is_monitor_item(type, 'CPU'):
                    cpu_grade = '-'
                else:
                    cpu_grade = alarm_event.get_grade('cpu', cpu)
                    if cur_info[node_name]['CPU'] != cpu_grade:
                        reason_json = {'value' : cpu}
                        reason.append(reason_json)
                        alarm_event.occur_event(conn, db_log, node_name, 'CPU', cur_info[node_name]['CPU'], cpu_grade, reason)
                LOG.info('[' + node_name + '][CPU][' + cpu_grade + ']' + str(reason))

            reason = []
            mem_grade = 'fail'
            if CONF.alarm().has_key('memory'):
                if not alarm_event.is_monitor_item(type, 'MEMORY'):
                    mem_grade = '-'
                else:
                    mem_grade = alarm_event.get_grade('memory', memory)
                    if cur_info[node_name]['MEMORY'] != mem_grade:
                        reason_json = {'value': memory}
                        reason.append(reason_json)
                        alarm_event.occur_event(conn, db_log, node_name, 'MEMORY', cur_info[node_name]['MEMORY'], mem_grade, reason)
                LOG.info('[' + node_name + '][MEMORY][' + mem_grade + ']' + str(reason))

            reason = []
            disk_grade = 'fail'
            if CONF.alarm().has_key('disk'):
                if not alarm_event.is_monitor_item(type, 'DISK'):
                    disk_grade = '-'
                else:
                    disk_grade = alarm_event.get_grade('disk', disk)
                    if cur_info[node_name]['DISK'] != disk_grade:
                        reason_json = {'value': disk}
                        reason.append(reason_json)
                        alarm_event.occur_event(conn, db_log, node_name, 'DISK', cur_info[node_name]['DISK'], disk_grade, reason)
                LOG.info('[' + node_name + '][DISK][' + disk_grade + ']' + str(reason))

            try:
                sql = 'UPDATE ' + DB.STATUS_TBL + \
                      ' SET CPU = \'' + cpu_grade + '\',' + \
                      ' MEMORY = \'' + mem_grade + '\',' + \
                      ' DISK = \'' + disk_grade + '\',' + \
                      ' NETWORK = \'' + network + '\',' + \
                      ' ONOS_APP = \'' + onos_app + '\',' + \
                      ' ONOS_REST = \'' + onos_rest + '\',' + \
                      ' ONOS_OPENFLOW = \'' + onos_of + '\',' + \
                      ' ONOS_CLUSTER = \'' + onos_cluster + '\',' + \
                      ' XOS_SVC = \'' + xos_status + '\',' + \
                      ' SYNCHRONIZER = \'' + synchronizer_status + '\',' + \
                      ' SWARM_NODE = \'' + swarm_node + '\',' + \
                      ' OPENSTACK_NODE = \'' + openstack_node + '\',' + \
                      ' SWARM_SVC = \'' + swarm_svc + '\',' + \
                      ' GATEWAY = \'' + v_router + '\',' + \
                      ' HA_SVC = \'' + ha_svc + '\',' + \
                      ' HA_RATIO = \'' + ha_ratio + '\',' + \
                      ' TRAFFIC_GW = \'' + traffic_gw + '\',' + \
                      ' PORT_STAT_VXLAN = \'' + port_stat_vxlan + '\',' + \
                      ' TRAFFIC_CONTROLLER = \'' + traffic_controller + '\',' + \
                      ' TRAFFIC_INTERNAL = \'' + traffic_internal + '\',' + \
                      ' time = \'' + str(datetime.now()) + '\'' + \
                      ' WHERE nodename = \'' + node_name + '\''
                db_log.write_log('----- UPDATE TOTAL SYSTEM INFO -----\n' + sql)

                if DB.sql_execute(sql, conn) != 'SUCCESS':
                    db_log.write_log('[FAIL] TOTAL SYSTEM INFO DB Update Fail.')
            except:
                LOG.exception()
    except:
        LOG.exception()

    return pre_stat

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