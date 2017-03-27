from log_lib import LOG

class SYS():
    # key = onos_name
    # value = info_dic, it contains ip, conn state, app list & status...
    onos_list = {}
    
    onos_thr_flag = True
    onos_redraw_flag = False

    @ classmethod
    def set_onos_info(cls, onos_info):
        try:
            onos_dtl_list = {}

            # sample data
            onos_dtl_list['ip'] = '10.10.2.66'
            onos_dtl_list['ping_status'] = 'OK'

            cls.onos_list['onos1'] = onos_dtl_list

            onos_dtl_list['ip'] = '10.10.2.67'
            onos_dtl_list['ping_status'] = 'OK'

            cls.onos_list['onos2'] = onos_dtl_list
        except:
            LOG.exception_err_write()

    # inquery onos info
    @classmethod
    def inquiry_onos_info(cls):
        try:
            onos_info = ''

            # parsing & set data

            return onos_info
        except:
            # except handling
            LOG.exception_err_write()

    @classmethod
    def get_onos_list(cls):
        return cls.onos_list.keys()

    @classmethod
    def get_onos_line_count(cls):
        # calc line count
        line_count = len(cls.onos_list.keys())

        return line_count

    @classmethod
    def changed_onos_info(cls, new_info):
        # if changed : return true
        return True

    @classmethod
    def get_onos_thr_flag(cls):
        return cls.onos_thr_flag

    @classmethod
    def set_onos_thr_flag(cls, ret):
        cls.onos_thr_flag = ret

    @classmethod
    def get_onos_redraw_flag(cls):
        return cls.onos_redraw_flag

    @ classmethod
    def set_onos_redraw_flag(cls, ret):
        cls.onos_redraw_flag = ret
