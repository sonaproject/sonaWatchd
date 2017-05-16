from datetime import datetime
import monitor.resource as res

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

        with DB.connection() as conn:
            url_info = conn.cursor().execute(sql).fetchall()

        conn.close()

        # if already exist
        if len(url_info) == 1:
            res_body = {'Result': 'SUCCESS'}
        else:
            # insert db
            sql = 'INSERT INTO ' + DB.REGI_SYS_TBL + ' VALUES (\'' + url  + '\', \'' + auth + '\' )'

            ret = DB.sql_execute(sql)

            if ret == 'SUCCESS':
                res_body = {'Result': 'SUCCESS'}
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
        nodes_info = get_node_list(node, 'nodename, ping, app', DB.STATUS_TBL)

        result = dict()

        for nodename, ping, app in nodes_info:
            result[nodename] = {'IP': ping, 'APP': app}

        return result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}

def proc_dis_resource(node, param):
    res_result = dict()

    nodes_info = get_node_list(node, 'nodename, ' + param, DB.STATUS_TBL)

    LOG.info('*****' + str(nodes_info))

    for nodename, value in nodes_info:
        if value < 0:
            res_result[nodename] = 'FAIL'
        else:
            res_result[nodename] = value

    return res_result


def proc_dis_onos(system, param):
    pass


def proc_dis_log(system, param):
    pass


def proc_dis_vrouter(system, param):
    pass


def proc_dis_swarm(system, param):
    pass


def proc_dis_xos(system, param):
    pass


def proc_dis_onosha(system, param):
    pass


def proc_dis_node(system, param):
    pass


def proc_dis_connection(system, param):
    pass


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
