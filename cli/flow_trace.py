from config import CONFIG
from log_lib import LOG
from subprocess import Popen, PIPE

class TRACE():
    TRACE_LOG = None
    trace_l2_cond_list = []
    trace_l3_cond_list = []

    compute_id = ''
    compute_list = {}

    cookie_list = []

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
        cls.compute_id = CONFIG.get_trace_cpt_id()
        cpt_list = CONFIG.get_trace_cpt_list()

        for cpt in cpt_list.split(','):
            cpt = cpt.strip()

            tmp = cpt.split(':')

            if len(tmp) == 2:
                cls.compute_list[tmp[0]] = tmp[1]

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


    ssh_options = '-o StrictHostKeyChecking=no ' \
                  '-o ConnectTimeout=' + str(CONFIG.get_ssh_timeout())
    @classmethod
    def exec_trace(cls, username, node, command):
        command = 'sudo ovs-appctl ofproto/trace br-int \'' + command + '\''

        cls.TRACE_LOG.trace_log('START TRACE | username = ' + username + ', ip = ' + node + ', condition = ' + command)

        cmd = 'ssh %s %s@%s %s' % (cls.ssh_options, username, node, command)
        cls.TRACE_LOG.trace_log('Command: ' + cmd)

        cls.get_cookie_list(username, node)

        return cls.parsing(cls.ssh_exec(cmd))


    @classmethod
    def get_cookie_list(cls, username, node):
        command = 'ovs-ofctl -O OpenFlow13 dump-flows br-int'

        cls.TRACE_LOG.trace_log('GET COOKIES | username = ' + username + ', ip = ' + node + ', condition = ' + command)

        cmd = 'ssh %s %s@%s %s' % (cls.ssh_options, username, node, command)
        cls.TRACE_LOG.trace_log('Command: ' + cmd)

        result = cls.ssh_exec(cmd)

        for cookie in cls.cookie_list:
            cls.cookie_list.remove(cookie)

        for line in result.splitlines():
            if 'cookie' in line:
                cookie = line.split(',')[0].split('=')[1].strip()
                LOG.debug_log('insert cookie = ' + cookie)
                cls.cookie_list.append(cookie)


    @classmethod
    def ssh_exec(cls, cmd):
        try:
            result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
            output, error = result.communicate()

            if result.returncode != 0:
                cls.TRACE_LOG.trace_log("SSH_Cmd Fail, cause => " + error)
                return 'SSH FAIL\nCOMMAND = ' + cmd + '\nREASON = ' + error
            else:
                cls.TRACE_LOG.trace_log("ssh command execute successful\n" + output)
                return output
        except:
            LOG.exception_err_write()
            return 'error'


    @classmethod
    def parsing(cls, output):
        try:
            result_flow = ''
            lines = output.splitlines()

            is_br_int = False
            for line in lines:
                line = line.strip()

                if line.startswith('Rule:'):
                    cookie = line.split(' ')[2].split('=')[1].strip()

                    if not cookie == '0':
                        if cookie in cls.cookie_list:
                            if not is_br_int:
                                result_flow = result_flow + '-------------------------------- br-int --------------------------------\n'
                            is_br_int = True
                        else:
                            if is_br_int:
                                result_flow = result_flow + '----------------------------- other bridge -----------------------------\n'
                            is_br_int = False

                    result_flow = result_flow + line + '\n'
                elif line.startswith('OpenFlow actions='):
                    result_flow = result_flow + line + '\n\n'

            return result_flow
        except:
            LOG.exception_err_write()
            return 'parsing error\n' + output