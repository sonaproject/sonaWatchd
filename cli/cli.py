import threading
import requests
import json
import base64
import readline

from config import CONFIG
from onos_info import ONOS
from log_lib import LOG

class CLI():
    command_list = []
    cli_validate_list = []
    cli_search_list = []
    cli_search_list_sub = {}

    cli_ret_flag = False
    selected_sys = 'all'

    CLI_LOG = None

    @classmethod
    def set_cli_log(cls, cli_log):
        cls.CLI_LOG = cli_log

    @classmethod
    def input_cmd(cls):
        try:
            cmd = raw_input('CLI(' + cls.selected_sys + ')> ')

            return cmd
        except:
            LOG.exception_err_write()

            return ''

    @classmethod
    def send_cmd(cls, cmd):
        try:
            # remove space
            cmd = cmd.strip()

            if cmd in ['quit', 'exit', 'menu']:
                cls.set_cli_ret_flag(True)
                return
            elif cmd not in cls.cli_validate_list:
                print '[' + cmd + '] is undefined command.'
                cls.set_cli_ret_flag(True)
                return
            elif cmd.startswith('sys '):
                cls.set_cli_ret_flag(True)

                tmp = cmd.split(' ')
                if len(tmp) == 2:
                    cls.selected_sys = (cmd.split(' '))[1]
                    return

            cls.set_cli_ret_flag(False)

            id = CONFIG.get_rest_id().strip()
            pw = CONFIG.get_rest_pw().strip()
            auth = id + ':' + pw

            tmp = cmd.split(' ')
            cmd = tmp[0]
            param = ''

            if len(tmp) == 2:
                param = tmp[1]

            req_body = {'command' : cmd, 'system' : cls.selected_sys, 'param' : param}
            req_body_json = json.dumps(req_body)

            header = {'Content-Type': 'application/json', 'Authorization': base64.b64encode(auth),
                      'Content-Length': len(req_body_json)}

            try:
                tmr = threading.Timer(3, cls.check_timeout)
                tmr.start()

                url = CONFIG.get_rest_addr()
                cls.CLI_LOG.cli_log('url check' + url)

                #post version
                myResponse = requests.post(url, headers=header, data=req_body_json, timeout=2)

                cls.CLI_LOG.cli_log('SEND REQ | cmd = ' + cmd + ', system = ' + cls.selected_sys + ' [' + id + ':' + pw + ']')
            except:
                # req timeout
                LOG.exception_err_write()
                return

            cls.set_cli_ret_flag(True)

            if (myResponse.status_code == 200):
                print 'response-code = ' + str(myResponse.status_code)
                print 'content = ' + myResponse.content
            else:
                print 'response-code = ' + str(myResponse.status_code)
                print 'content = ' + myResponse.content

            cls.CLI_LOG.cli_log('RECV RES | response-code = ' + str(myResponse.status_code) + ', content = ' + myResponse.content)

            jData = json.loads(myResponse.content.replace("\'", '"'))

            # debugging code
            print json.dumps(jData, sort_keys=True, indent=4)
        except:
            LOG.exception_err_write()

    @classmethod
    def check_timeout(cls):

        if cls.get_cli_ret_flag():
            return

        print 'Processing timeout.'

        cls.set_cli_ret_flag(True)

    @classmethod
    def set_search_list(cls):
        try:
            for cmd in cls.command_list:
                cls.cli_search_list.append(cmd)
                cls.cli_validate_list.append(cmd)

                if (CONFIG.get_config_instance().has_section(cmd)):
                    opt_list = CONFIG.cli_get_value(cmd, CONFIG.get_cmd_opt_key_name())
                    tmp = []
                    for opt in opt_list.split(','):
                        tmp.append(opt.strip())
                        cls.cli_validate_list.append(cmd + ' ' + opt.strip())
                    cls.cli_search_list_sub[cmd] = tmp

            cls.cli_search_list.append('menu')
            cls.cli_search_list.append('quit')
            cls.cli_search_list.append('exit')
            cls.cli_search_list.append('sys')

            tmp_sys = []
            tmp_sys.append('all')
            cls.cli_validate_list.append('sys all')
            for onos_name in ONOS.get_onos_list():
                tmp_sys.append(onos_name)
                cls.cli_validate_list.append('sys ' + onos_name)
            cls.cli_search_list_sub['sys'] = tmp_sys
        except:
            LOG.exception_err_write()

    @classmethod
    def complete_cli(cls, text, state, search_list):
        try:
            for cmd in search_list:
                if cmd.startswith(text):
                    if not state:
                        return str(cmd)
                    else:
                        state -= 1
        except:
            LOG.exception_err_write()

    @classmethod
    def pre_complete_cli(cls, text, state):
        try:
            BUFFER = readline.get_line_buffer()
            args = [None, None, None, None, None, None, None, None, None, None]
            argtemp = []
            if BUFFER != "":
                i = -1
                while i != BUFFER.count(" "):
                    if BUFFER.count(" ") >= 0:
                        if BUFFER.count(" ") == 0:  # 1 because len() starts couting at 1
                            return cls.complete_cli(text, state, cls.get_cli_search_list())
                        else:
                            #                    print "Else triggered"
                            index = 0
                            cmd = []
                            while cls.complete_cli(BUFFER.split()[0], index, cls.get_cli_search_list()):
                                cmd.append(cls.complete_cli(BUFFER.split()[0], index, cls.get_cli_search_list()))
                                index = index + 1
                            if len(cmd) == 1:
                                cmd = cmd[0]
                    if BUFFER.count(" ") >= 1:
                        if BUFFER.count(" ") == 1:
                            cmd = BUFFER.split()[0]

                            if cls.cli_search_list_sub.has_key(cmd):
                                # print 'step2 text = ' + text + " state = " + str(state)
                                return cls.complete_cli(text, state, cls.cli_search_list_sub[cmd])
                        else:
                            index = 0
                            while cls.complete_cli(BUFFER[1], index, cls.cli_search_list_sub[cmd]):
                                argtemp.append(cls.complete_cli(BUFFER[1], index, cls.cli_search_list_sub[cmd]))
                                index = index + 1
                            if len(argtemp) == 1:
                                argtemp == argtemp[0]
                    i = i + 1
            else:
                return cls.complete_cli(text, state, cls.get_cli_search_list())
        except:
            LOG.exception_err_write()

    @classmethod
    def set_cmd_list(cls):
        cls.command_list = CONFIG.get_cmd_list()

    @classmethod
    def get_cli_search_list(cls):
        return cls.cli_search_list

    @classmethod
    def get_cli_ret_flag(cls):
        return cls.cli_ret_flag

    @classmethod
    def set_cli_ret_flag(cls, ret):
        cls.cli_ret_flag = ret
