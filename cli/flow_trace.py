import readline

from config import CONFIG
from log_lib import LOG

class TRACE():
    TRACE_LOG = None
    trace_l2_cond_list = []
    trace_l3_cond_list = []

    @classmethod
    def set_trace_log(cls, trace_log):
        cls.TRACE_LOG = trace_log

    @classmethod
    def send_trace(cls, ip, condition):
        try:
            # req trace
            cls.TRACE_LOG.trace_log('START TRACE | ip = ' + ip + ', condition = ' + condition)
        except:
            LOG.exception_err_write()

    @classmethod
    def set_cnd_list(cls):
        cls.trace_l2_cond_list = CONFIG.get_cnd_list('l2')
        cls.trace_l3_cond_list = CONFIG.get_cnd_list('l3')

    @staticmethod
    def valid_IPv4(address):
        try:
            parts = address.split(".")

            if len(parts) != 4:
                return False
            for item in parts:
                if len(item) > 3:
                    return False
                if not 0 <= int(item) <= 255:
                    return False
            return True
        except:
            LOG.exception_err_write()
            return False