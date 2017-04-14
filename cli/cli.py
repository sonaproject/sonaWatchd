import threading
import requests
import json
import base64
import readline

from config import CONFIG
from system_info import SYS
from log_lib import LOG

class CLI():
    command_list = []
    cli_validate_list = []
    cli_search_list = []
    cli_search_list_sub = {}

    cli_ret_flag = False
    selected_sys = 'all'

    CLI_LOG = None

    modify_flag = False
    save_buffer = ''

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
            cls.CLI_LOG.cli_log('START SEND COMMAND = ' + cmd)
            # remove space
            cmd = cmd.strip()

            if cmd in ['quit', 'exit', 'menu']:
                cls.set_cli_ret_flag(True)
                return
            elif len(cmd.strip()) == 0:
                cls.set_cli_ret_flag(True)
                return
            elif cmd not in cls.cli_validate_list:
                if cmd.startswith('sys'):
                    tmp = cmd.split(' ')
                    if len(tmp) == 1:
                        print 'system name is missing.'
                    if len(tmp) >= 2:
                        print '[' + cmd[4:] + '] is invalid system name.'
                else:
                    print '[' + cmd + '] is undefined command.'
                cls.set_cli_ret_flag(True)
                return
            elif cmd.startswith('sys '):
                cls.set_cli_ret_flag(True)

                tmp = cmd.split(' ')
                if len(tmp) == 2:
                    cls.selected_sys = (cmd.split(' '))[1]
                    cls.CLI_LOG.cli_log('CHANGE TARGET SYSTEM = ' + cls.selected_sys)
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

            header = {'Content-Type': 'application/json', 'Authorization': base64.b64encode(auth)}

            cls.CLI_LOG.cli_log('---------------------------SEND CMD---------------------------')

            try:
                tmr = threading.Timer(3, cls.check_timeout)
                tmr.start()

                url = CONFIG.get_rest_addr()
                cls.CLI_LOG.cli_log('URL = ' + url)
                cls.CLI_LOG.cli_log('AUTH = ' + id + ':' + pw)

                myResponse = requests.get(url, headers=header, data=req_body_json, timeout=10)

                cls.CLI_LOG.cli_log('COMMAND = ' + cmd)
                cls.CLI_LOG.cli_log('SYSTEM = ' + cls.selected_sys)
                cls.CLI_LOG.cli_log('HEADER = ' + json.dumps(header, sort_keys=True, indent=4))
                cls.CLI_LOG.cli_log('BODY = ' + json.dumps(req_body, sort_keys=True, indent=4))

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

            cls.CLI_LOG.cli_log('---------------------------RECV RES---------------------------')
            cls.CLI_LOG.cli_log('RESPONSE CODE = ' + str(myResponse.status_code))

            try:
                cls.CLI_LOG.cli_log('BODY = ' + json.dumps(json.loads(myResponse.content.replace("\'", '"')), sort_keys=True, indent=4))
            except:
                cls.CLI_LOG.cli_log('BODY = ' + myResponse.content)

        except:
            LOG.exception_err_write()

    @classmethod
    def check_timeout(cls):

        if cls.get_cli_ret_flag():
            return

        cls.CLI_LOG.cli_log('PROCESSING TIMEOUT')
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
            for onos_name in SYS.get_onos_list():
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

            argtemp = []
            if BUFFER != "":
                i = -1
                while i != BUFFER.count(" "):
                    if BUFFER.count(" ") >= 0:
                        if BUFFER.count(" ") == 0:
                            return cls.complete_cli(text, state, cls.get_cli_search_list())
                        else:
                            # mac OS
                            if 'libedit' in readline.__doc__:
                                if cls.modify_flag:
                                    if cls.save_buffer != BUFFER:
                                        cls.modify_flag = False
                                    else:
                                        return cls.complete_cli(text, state, cls.get_cli_search_list())

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

    @staticmethod
    def is_menu(cmd):
        if cmd == 'menu':
            return True

        return False

    @staticmethod
    def is_exit(cmd):
        if cmd == 'quit' or cmd == 'exit':
            return True

        return False
