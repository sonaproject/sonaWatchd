import readline

from config import CONFIG
from log_lib import LOG

class TRACE():
    TRACE_LOG = None
    trace_search_list = []

    @classmethod
    def set_trace_log(cls, trace_log):
        cls.TRACE_LOG = trace_log

    @classmethod
    def set_search_list(cls):
        # set trace condition
        cls.trace_search_list.append('menu')
        cls.trace_search_list.append('quit')
        cls.trace_search_list.append('exit')

    @classmethod
    def imput_trace(cls):
        try:
            while True:
                ip = raw_input('Flow Trace> Target(ip) : ')

                if TRACE.valid_IPv4(ip):
                    break

                print '[' + ip + '] invalid IP address.'

            readline.set_completer(cls.complete_trace)

            condition = raw_input('Flow Trace(' + ip + ')> Input Condition : ')
        except:
            LOG.exception_err_write()

        return ip, condition

    @classmethod
    def send_trace(cls, ip, condition):
        try:
            # req trace
            cls.TRACE_LOG.trace_log('START TRACE | ip = ' + ip + ', condition = ' + condition)
        except:
            LOG.exception_err_write()

    @classmethod
    def set_cnd_list(cls):
        cls.trace_search_list = CONFIG.get_cnd_list()

    @classmethod
    def complete_trace(cls, text, state):
        try:
            for cond in cls.trace_search_list:
                if cond.startswith(text):
                    if not state:
                        return str(cond)
                    else:
                        state -= 1
        except:
            LOG.exception_err_write()

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