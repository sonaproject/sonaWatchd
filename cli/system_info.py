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
            #{"command": "dis-resource", "system": "test", "param": "test", "result": "{'ONOS2': {'IP': 'ok', 'APP': 'nok'}, 'ONOS3': {'IP': 'ok', 'APP': 'nok'}, 'ONOS1': {'IP': 'ok', 'APP': 'nok'}}"}

            sys_info = json.loads(sys_info)
            sys_info = sys_info['result']

            cls.pre_sys_info = sys_info

            for key in sys_info:
                dtl_list = {}

                dtl_list['ping'] = sys_info[key]['ping']
                dtl_list['app'] = sys_info[key]['app']
                dtl_list['cpu'] = sys_info[key]['cpu']
                dtl_list['memory'] = sys_info[key]['memory']
                dtl_list['disk'] = sys_info[key]['disk']

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
        cls.last_check_time = new_sys_info['time']

        if cls.pre_sys_info == new_sys_info['result']:
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

