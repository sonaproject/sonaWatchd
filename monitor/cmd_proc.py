import json
from api.sona_log import LOG

class CMD_PROC():
    @staticmethod
    def parse_req(req):
        res_body = {}

        try:
            cmd = req['command']
            system = req['system']
            param = req['param']

            res_body['command'] = cmd
            res_body['system'] = system
            res_body['param'] = param

            # must have exception handling
            ret = func_map[cmd](system, param)

            res_body['result'] = ret

        except:
            LOG.exception()

        return res_body

    @staticmethod
    def proc_dis_resource(system, param):
        res = "return proc_dis_resource [sys = " + system + " param = " + param + "]"
        LOG.info('[CMD_PROC] res_msg = ' + res)

        return res

    @staticmethod
    def proc_dis_onos(system, param):
        res = "return proc_dis_onos [sys = " + system + " param = " + param + "]"
        LOG.info('[CMD_PROC] res_msg = ' + res)

        return res

    @staticmethod
    def proc_dis_log(system, param):
        res = "return proc_dis_log [sys = " + system + " param = " + param + "]"
        LOG.info('[CMD_PROC] res_msg = ' + res)

        return res

func_map = {'dis-resource': CMD_PROC.proc_dis_resource,
            'dis-onos': CMD_PROC.proc_dis_onos,
            'dis-log': CMD_PROC.proc_dis_log}