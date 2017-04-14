import json
from log_lib import LOG

class SYS():
    # key = system name
    # value = info_dic, it contains ip, conn state
    sys_list = {}
    last_check_time = ''

    sys_thr_flag = True
    sys_redraw_flag = False

    pre_sys_info = ''

    @classmethod
    def set_sys_info(cls, sys_info):
        try:
            #{"command": "dis-resource", "system": "test", "param": "test", "result": ["2017-04-07 17:25:44.092887",
            #                                                                         "{'ONOS2': {'IP': 'ok', 'APP': 'nok'}, 'ONOS3': {'IP': 'ok', 'APP': 'nok'}, 'ONOS1': {'IP': 'ok', 'APP': 'nok'}}"]}
            sys_info = json.loads(sys_info)

            result = sys_info['result']

            cls.last_check_time = result[0]
            sys_info = result[1]

            cls.pre_sys_info = sys_info

            #sys_info = json.loads(json.dumps(sys_info.replace("\'", '"')))
            sys_info = eval(sys_info)

            for key in sys_info:
                dtl_list = {}

                LOG.debug_log('KEY = ' + key)

                dtl_list['IP'] = sys_info[key]['IP']
                dtl_list['APP'] = sys_info[key]['APP']

                cls.sys_list[key] = dtl_list
        except:
            LOG.exception_err_write()

    @classmethod
    def get_sys_list(cls):
        return cls.sys_list.keys()

    @classmethod
    def get_sys_line_count(cls):
        # calc line count
        line_count = len(cls.sys_list.keys())

        return line_count

    @classmethod
    def changed_sys_info(cls, new_info):
        # if changed : return true
        new_sys_info = json.loads(new_info)
        new_result = new_sys_info['result']
        cls.last_check_time = new_result[0]

        if cls.pre_sys_info == new_result[1]:
            return False
        else:
            cls.set_sys_info(new_info)
            return True

    @classmethod
    def get_sys_thr_flag(cls):
        return cls.sys_thr_flag

    @classmethod
    def set_sys_thr_flag(cls, ret):
        cls.sys_thr_flag = ret

    @classmethod
    def get_sys_redraw_flag(cls):
        return cls.sys_redraw_flag

    @classmethod
    def set_sys_redraw_flag(cls, ret):
        cls.sys_redraw_flag = ret

