from datetime import datetime
import monitor.resource as res

from api.sona_log import LOG
from api.watcherdb import DB

def parse_command(command):
    try:
        res_body = dict()
        res_body['command'] = command['command']
        res_body['system'] = command['system']

        try:
            res_body['param'] = command['param']
        except:
            res_body['param'] = ''

        ret = COMMAND_MAP[command['command']](command['system'], command['param'])
        res_body['result'] = ret
        res_body['time'] = str(datetime.now())

        return res_body
    except:
        return LOG.exception()

def proc_dis_system(node, dummy):
    try:
        nodes_info = get_node_list(node, 'nodename, ping, app')

        result = dict()

        for nodename, ping, app in nodes_info:
            result[nodename] = {'IP': ping, 'APP': app}

        return result
    except:
        LOG.exception()

def proc_dis_resource(node, param):
    nodes_info = get_node_list(node, 'nodename, ip_addr, username, ping')

    LOG.info("Get Resource Usage ... %s %s", nodes_info, param)
    resource_usage = res.get_resource_usage(nodes_info, param)

    return resource_usage


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


def get_node_list(nodes, param):
    try:
        if nodes == 'all':
            sql = 'SELECT ' + param + ' FROM ' + DB.NODE_INFO_TBL
        else:
            sql = 'SELECT ' + param + ' FROM ' + DB.NODE_INFO_TBL + ' WHERE nodename = \'' + nodes + '\''

        with DB.connection() as conn:
            nodes_info = conn.cursor().execute(sql).fetchall()

        conn.close()
        return nodes_info
    except:
        LOG.exception()

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
