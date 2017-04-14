import json
from api.sona_log import LOG
from api.watcherdb import DB
import monitor.resource as res


def parse_command(command):

    res_body = dict()
    res_body['command'] = command['command']
    res_body['system'] = command['system']
    res_body['param'] = command['param']

    ret = COMMAND_MAP[command['command']](command['system'], command['param'])
    res_body['result'] = ret

    return res_body

    pass

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


def proc_dis_k8s(system, param):
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
                sql = 'SELECT * FROM ' + DB.DB_NODE_TABLE
                nodes_info = conn.cursor().execute(sql).fetchall()
                conn.commit()
                return nodes_info
        else:
            with DB.connection() as conn:
                sql = 'SELECT * FROM ' + DB.DB_NODE_TABLE + ' WHERE nodename=' + nodes
                node_info = conn.cursor().execute(sql).fetchall()
                conn.commit()
                return node_info
    except:
        LOG.exception()

COMMAND_MAP = {'dis-resource': proc_dis_resource,
               'dis-onos': proc_dis_onos,
               'dis-log': proc_dis_log,
               'dis-vrouter': proc_dis_vrouter,
               'dis-k8s': proc_dis_k8s,
               'dis-xos': proc_dis_xos,
               'dis-onosha': proc_dis_onosha,
               'dis-node': proc_dis_node,
               'dis-connection': proc_dis_connection,
               'dis-all': proc_dis_all,
               #internal command
               'dis-system':proc_dis_system}


# class CMD_PROC():
#
#     @staticmethod
#     def parse_command(req):
#         res_body = {}
#
#         try:
#             cmd = req['command']
#             system = req['system']
#             param = req['param']
#
#             res_body['command'] = cmd
#             res_body['system'] = system
#             res_body['param'] = param
#
#             ret = func_map[cmd](system, param)
#             res_body['result'] = ret
#
#         except:
#             LOG.exception()
#
#         return res_body
#
#     @staticmethod
#     def exist_command(req):
#         cmd = req['command']
#
#         if cmd not in func_map.keys():
#             return False
#         return True
#
#     @staticmethod
#     def proc_dis_resource(system, param):
#
#         result = dict()
#
#         if param == 'disk':
#             result['disk'] = res.get_disk_usage(system)
#
#         # with DB.connection() as conn:
#         #     item, time, data = conn.cursor().execute("SELECT * FROM t_status WHERE item='main_status'").fetchone()
#         #     LOG.info('Get periodic data: %s %s', time, data)
#
#         LOG.info('Resource --> %s', result)
#         return result
#
#     @staticmethod
#     def proc_dis_onos(system, param):
#         res = "return proc_dis_onos [sys = " + system + " param = " + param + "]"
#         LOG.info('[CMD_PROC] RES MSG = ' + res)
#
#         return res
#
#     @staticmethod
#     def proc_dis_log(system, param):
#         res = "return proc_dis_log [sys = " + system + " param = " + param + "]"
#         LOG.info('[CMD_PROC] RES MSG = ' + res)
#
#         return res
#
# func_map = {'dis-resource': CMD_PROC.proc_dis_resource,
#             'dis-onos': CMD_PROC.proc_dis_onos,
#             'dis-log': CMD_PROC.proc_dis_log}
