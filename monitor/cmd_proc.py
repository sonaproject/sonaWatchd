from api.sona_log import LOG
from api.watcherdb import DB
import monitor.resource as res


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

        return res_body
    except:
        return LOG.exception()

def proc_dis_system(node, param):
    with DB.connection() as conn:
        item, time, data = conn.cursor().execute("SELECT * FROM " + DB.DB_STATUS_TABEL + " WHERE item='main_status'").fetchone()
        LOG.info('Get \'periodic\' data: %s %s', time, data)
    return [time, data]

def proc_dis_resource(node, param):
    nodes_info = get_node_list(node)

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


def get_node_list(nodes):
    try:
        if nodes == 'all':
            with DB.connection() as conn:
                sql = 'SELECT nodename, ip_addr, username FROM ' + DB.NODE_INFO_TBL
                nodes_info = conn.cursor().execute(sql).fetchall()
                conn.commit()
                return nodes_info
        else:
            with DB.connection() as conn:
                sql = 'SELECT nodename, ip_addr, username FROM ' + DB.NODE_INFO_TBL + ' WHERE nodename=' + nodes
                node_info = conn.cursor().execute(sql).fetchall()
                conn.commit()
                return node_info
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
