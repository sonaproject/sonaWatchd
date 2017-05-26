import json
from datetime import datetime

from api.sbapi import SshCommand
from api.sona_log import LOG
from api.watcherdb import DB

def parse_command(req_obj):
    try:
        res_body = dict()
        res_body['command'] = req_obj['command']
        res_body['system'] = req_obj['system']

        try:
            res_body['param'] = req_obj['param']
        except:
            res_body['param'] = ''

        ret = COMMAND_MAP[req_obj['command']](req_obj['system'], req_obj['param'])
        res_body['result'] = ret
        res_body['time'] = str(datetime.now())

        return res_body
    except:
        LOG.exception()
        return {'Result': 'FAIL'}

def regi_url(url, auth):
    try:
        sql = 'SELECT * FROM ' + DB.REGI_SYS_TBL + ' WHERE url = \'' + url + '\''
        sql_evt = 'SELECT * FROM ' + DB.EVENT_TBL

        with DB.connection() as conn:
            url_info = conn.cursor().execute(sql).fetchall()
            evt_list = conn.cursor().execute(sql_evt).fetchall()
        conn.close()

        event_list = []

        for nodename, item, grade, desc, time in evt_list:
            if not grade in ['ok', 'normal']:
                evt = {'event': 'occur', 'system': nodename, 'item': item, 'grade': grade, 'desc': desc, 'time': time}
                event_list.append(evt)

        # if already exist
        if len(url_info) == 1:
            res_body = {'Result': 'SUCCESS', 'Event list': event_list}
        else:
            # insert db
            sql = 'INSERT INTO ' + DB.REGI_SYS_TBL + ' VALUES (\'' + url  + '\', \'' + auth + '\' )'

            ret = DB.sql_execute(sql)

            if ret == 'SUCCESS':
                res_body = {'Result': 'SUCCESS', 'Event list': event_list}
            else:
                res_body = {'Result': 'FAIL'}

        return res_body
    except:
        LOG.exception()
        return {'Result': 'FAIL'}

def unregi_url(url):
    try:
        sql = 'SELECT * FROM ' + DB.REGI_SYS_TBL + ' WHERE url = \'' + url + '\''

        with DB.connection() as conn:
            url_info = conn.cursor().execute(sql).fetchall()

        conn.close()

        # if no exist
        if len(url_info) == 0:
            res_body = {'Result': 'SUCCESS'}
        else:
            # delete db
            sql = 'DELETE FROM ' + DB.REGI_SYS_TBL + ' WHERE url = \'' + url + '\''

            ret = DB.sql_execute(sql)

            if ret == 'SUCCESS':
                res_body = {'Result': 'SUCCESS'}
            else:
                res_body = {'Result': 'FAIL'}

        return res_body
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_system(node, dummy):
    try:
        nodes_info = get_node_list(node, 'nodename, ' + DB.item_list, DB.STATUS_TBL)

        result = dict()

        for nodename, ping, app, web, cpu, memory, disk, ovsdb, of, cluster, node, vrouter, ha_status in nodes_info:
            node_type = get_node_list(nodename, 'type')

            if 'ONOS' in str(node_type).upper():
                result[nodename] = {'ping': ping, 'app': app, 'web': web, 'cpu': cpu, 'memory': memory, 'disk': disk,
                                    'ovsdb': ovsdb, 'of': of, 'cluster': cluster, 'ha_status': ha_status}
            elif 'SWARM' in str(node_type).upper():
                result[nodename] = {'ping': ping, 'app': app, 'cpu': cpu, 'memory': memory, 'disk': disk, 'node': node}
            elif 'OPENSTACK' in str(node_type).upper():
                result[nodename] = {'ping': ping, 'cpu': cpu, 'memory': memory, 'disk': disk, 'vrouter': vrouter}
            else:
                result[nodename] = {'ping': ping, 'app': app, 'cpu': cpu, 'memory': memory, 'disk': disk}

        return result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}

def proc_dis_resource(node, param):
    nodes_info = get_node_list(node, 'nodename, ' + param, DB.RESOURCE_TBL)

    if len(nodes_info) == 0:
        return {'fail': 'This is not a command on the target system.'}

    res_result = dict()
    for nodename, value in nodes_info:
        if value < 0:
            res_result[nodename] = 'FAIL'
        else:
            res_result[nodename] = value

    return res_result


def proc_dis_onos(node, param):
    if param == 'app':
        nodes_info = get_node_list(node, 'nodename, applist', DB.ONOS_TBL)

    if param == 'web':
        nodes_info = get_node_list(node, 'nodename, weblist', DB.ONOS_TBL)

    if len(nodes_info) == 0:
        return {'fail': 'This is not a command on the target system.'}

    res_result = dict()
    for nodename, list in nodes_info:
        if list == 'fail' or list == 'none':
            res_result[nodename] = 'FAIL'
        else:
            res_result[nodename] = list

    return res_result


def proc_dis_log(node, param):
    cmd = 'ld'

    if param == 'debug':
        cmd = 'ld -l DEBUG'
    elif param == 'info':
        cmd = 'ld -l INFO'
    elif param == 'error':
        cmd = 'ld -l ERROR'
    elif param == 'exception':
        cmd = 'log:exception-display'

    nodes_info = get_node_list(node, 'nodename, ip_addr, type')

    res_result = dict()
    for node_name, ip, type in nodes_info:
        if type.upper() == 'ONOS':
            log_crt = SshCommand.onos_ssh_exec(ip, cmd)

            if log_crt is not None:
                res_result[node_name] = log_crt
            else:
                res_result[node_name] = 'FAIL'

    return res_result


def proc_dis_vrouter(node, param):
    nodes_info = get_node_list(node, 'nodename, ' + param, DB.VROUTER_TBL)

    if len(nodes_info) == 0:
        return {'fail': 'This is not a command on the target system.'}

    res_result = dict()
    for nodename, list in nodes_info:
        if list == 'fail' or list == 'none':
            res_result[nodename] = 'FAIL'
        else:
            res_result[nodename] = list

    return res_result


def proc_dis_swarm(node, param):
    nodes_info = get_node_list(node, 'nodename, ' + param, DB.SWARM_TBL)

    if len(nodes_info) == 0:
        return {'fail': 'This is not a command on the target system.'}

    res_result = dict()
    for nodename, list in nodes_info:
        if list == 'fail' or list == 'none':
            res_result[nodename] = 'FAIL'
        else:
            res_result[nodename] = list

    return res_result


def proc_dis_xos(system, param):
    pass


def proc_dis_onosha(node, param):
    # check onos
    nodes_info = get_node_list(node, 'nodename', DB.ONOS_TBL)

    if len(nodes_info) == 0:
        return {'fail': 'This is not a command on the target system.'}

    sql = 'SELECT stats FROM ' + DB.HA_TBL + ' WHERE ha_key = \'HA\''

    with DB.connection() as conn:
        nodes_info = conn.cursor().execute(sql).fetchone()
    conn.close()

    for value in nodes_info:
        return json.loads(str(value).replace('\'', '\"'))

    return {'HA': 'FAIL'}

def proc_dis_node(system, param):
    pass


def proc_dis_connection(node, param):
    nodes_info = get_node_list(node, 'nodename, ' + param, DB.CONNECTION_TBL)

    if len(nodes_info) == 0:
        return {'fail': 'This is not a command on the target system.'}

    res_result = dict()
    for nodename, value in nodes_info:
        if value == 'none':
            res_result[nodename] = 'FAIL'
        else:
            res_result[nodename] = value

    return res_result


def proc_dis_all(system, param):
    pass


def exist_command(req):
    cmd = req['command']

    if cmd not in COMMAND_MAP.keys():
        return False
    return True


def get_node_list(nodes, param, tbl = DB.NODE_INFO_TBL):
    try:
        if nodes == 'all':
            sql = 'SELECT ' + param + ' FROM ' + tbl
        else:
            sql = 'SELECT ' + param + ' FROM ' + tbl + ' WHERE nodename = \'' + nodes + '\''

        with DB.connection() as conn:
            nodes_info = conn.cursor().execute(sql).fetchall()

        conn.close()
        return nodes_info
    except:
        LOG.exception()
        return None

COMMAND_MAP = {'dis-resource': proc_dis_resource,
               'dis-onos': proc_dis_onos,
               'dis-log': proc_dis_log,
               'dis-vrouter': proc_dis_vrouter,
               'dis-swarm': proc_dis_swarm,
               'dis-xos': proc_dis_xos,
               'dis-onosha': proc_dis_onosha,
               'dis-node': proc_dis_node,
               'dis-connection': proc_dis_connection,
               'dis-all': proc_dis_all,
               #internal command
               'dis-system':proc_dis_system}
