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
    HISTORY_LOG = None

    modify_flag = False
    save_buffer = ''

    @classmethod
    def set_cli_log(cls, cli_log, history_log):
        cls.CLI_LOG = cli_log
        cls.HISTORY_LOG = history_log

    @classmethod
    def input_cmd(cls):
        try:
            cmd = raw_input('CLI(' + cls.selected_sys + ')> ')

            return cmd
        except:
            LOG.exception_err_write()

            return ''

    @classmethod
    def process_cmd(cls, cmd):
        try:
            # remove space
            cmd = cmd.strip()

            if len(cmd.strip()) == 0:
                cls.set_cli_ret_flag(True)
                return
            elif (cmd.startswith('onos-shell ') or cmd.startswith('os-shell ')) and len(cmd.split(' ')) > 2:
                pass
            elif cmd not in cls.cli_validate_list:
                tmp = cmd.split(' ')

                if tmp[0] == 'sys':
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
            else:
                cls.set_cli_ret_flag(True)
                tmp = cmd.split(' ')

                if (len(tmp) == 1 and CONFIG.get_config_instance().has_section(cmd)):
                    param = CONFIG.cli_get_value(cmd, CONFIG.get_cmd_opt_key_name()).replace(',', '|')
                    param = param.replace(' ', '')
                    print 'This command requires parameter.'
                    print cmd + ' [' + param + ']'
                    return

            cls.set_cli_ret_flag(False)


            tmr = threading.Timer(3, cls.check_timeout)
            tmr.start()

            cls.CLI_LOG.cli_log('START SEND COMMAND = ' + cmd)

            ret_code, myResponse = cls.send_rest(cmd)

            # rest timeout
            if ret_code == -1:
                return

            cls.set_cli_ret_flag(True)

            if (myResponse.status_code == 200):
                cls.parsingRet(myResponse.content)
            else:
                print 'response-code = ' + str(myResponse.status_code)
                print 'content = ' + myResponse.content
        except:
            LOG.exception_err_write()

    @classmethod
    def parsingRet(cls, result):
        try:
            sys_info = json.loads(result)

            result = sys_info['result']

            if dict(result).has_key('fail'):
                print result['fail']
                return

            command = sys_info['command']
            param = sys_info['param']

            sorted_list = sorted(dict(result).keys())

            try:
                if command == 'resource':
                    data = []

                    for sys in sorted_list:
                        sys_ret = str(result[sys])
                        line = []
                        line.append(sys)
                        line.append(sys_ret)
                        data.append(line)

                    header = []

                    col_sys = dict()
                    col_sys['title'] = 'System'
                    col_sys['size'] = '10'

                    col_value = dict()
                    col_value['title'] = str(param)
                    col_value['size'] = '8'

                    header.append(col_sys)
                    header.append(col_value)

                    print ''
                    cls.draw_grid(header, data)
                    print ''

                elif command == 'onos-svc':
                    print('')
                    for sys in sorted_list:
                        print '[' + sys + ']'

                        sys_ret = result[sys]
                        if str(sys_ret).upper().endswith('FAIL'):
                            sys_ret = 'fail'
                            print sys_ret
                        else:
                            data = []

                            for row in sys_ret:
                                line = []

                                line.append(row['name'])
                                line.append(row['status'])
                                line.append(row['monitor_item'])

                                data.append(line)

                            header = []

                            col_name = dict()
                            col_name['title'] = 'Name'
                            col_name['size'] = '30'

                            col_status = dict()
                            col_status['title'] = 'Status'
                            col_status['size'] = '8'

                            col_monitor = dict()
                            col_monitor['title'] = 'Monitor Item'
                            col_monitor['size'] = '14'

                            header.append(col_name)
                            header.append(col_status)
                            header.append(col_monitor)

                            cls.draw_grid(header, data)

                        print ''

                elif command == 'ha-proxy':
                    print ''
                    print "+----------------------------------------------------------+"
                    print "|  Proxy Service Name  | Service Host |  Sts |  Req | Succ |"
                    print "+----------------------------------------------------------+"

                    for key in dict(result).keys():
                        for line in result[key]:
                            host = dict(line)['name']

                            if host == 'FRONTEND':
                                print "|%21s |%13s |%5s |%5s |%5s |" % (
                                    key, host, dict(line)['node_sts'], dict(line)['req_count'],
                                    dict(line)['succ_count'])

                    for key in dict(result).keys():
                        first_flag = 1;
                        for line in result[key]:
                            host = dict(line)['name']

                            if host == 'FRONTEND':
                                continue

                            if first_flag == 1:
                                print "|%21s |%13s |%5s |%5s |%5s |" % (
                                    key, host, dict(line)['node_sts'], dict(line)['req_count'],
                                    dict(line)['succ_count'])
                                first_flag = 0
                            else:
                                print "|%21s |%13s |%5s |%5s |%5s |" % (
                                    '', host, dict(line)['node_sts'], dict(line)['req_count'],
                                    dict(line)['succ_count'])
                    print "+-----------------------------------------------------------+"
                    print ''

                elif command == 'traffic-controller':
                    print('')
                    for sys in sorted_list:
                        print '[' + sys + ']'

                        sys_ret = result[sys]
                        if str(sys_ret).upper().endswith('FAIL'):
                            sys_ret = 'fail'
                            print sys_ret
                        else:
                            data = []

                            for row in sys_ret['stat_list']:

                                line = []

                                line.append(row['hostname'])
                                line.append(row['of_id'])
                                line.append(row['inbound'])
                                line.append(row['outbound'])
                                line.append(row['mod'])
                                line.append(row['removed'])
                                line.append(row['request'])
                                line.append(row['reply'])

                                data.append(line)

                            header = []

                            col_host = dict()
                            col_host['title'] = 'Host Name'
                            col_host['size'] = '12'

                            col_id = dict()
                            col_id['title'] = 'Switch ID'
                            col_id['size'] = '20'

                            col_in = dict()
                            col_in['title'] = 'INBOUND'
                            col_in['size'] = '8'

                            col_out = dict()
                            col_out['title'] = 'OUTBOUND'
                            col_out['size'] = '8'

                            col_mod = dict()
                            col_mod['title'] = 'MOD'
                            col_mod['size'] = '8'

                            col_remove = dict()
                            col_remove['title'] = 'REMOVE'
                            col_remove['size'] = '8'

                            col_req = dict()
                            col_req['title'] = 'REQUEST'
                            col_req['size'] = '8'

                            col_reply = dict()
                            col_reply['title'] = 'REPLY'
                            col_reply['size'] = '8'

                            header.append(col_host)
                            header.append(col_id)
                            header.append(col_in)
                            header.append(col_out)
                            header.append(col_mod)
                            header.append(col_remove)
                            header.append(col_req)
                            header.append(col_reply)

                            cls.draw_grid(header, data)

                            print ' * ' + sys_ret['description']
                        print ''

                elif command == 'openstack-node':
                    if param == 'list':
                        print('')
                        for sys in sorted_list:
                            print '[' + sys + ']'

                            sys_ret = result[sys]
                            if str(sys_ret).upper().endswith('FAIL'):
                                sys_ret = 'fail'
                                print sys_ret
                            else:
                                data = []

                                for row in sys_ret:
                                    line = []

                                    line.append(row['hostname'])
                                    line.append(row['type'])
                                    line.append(row['management_ip'])
                                    line.append(row['data_ip'])
                                    line.append(row['state'])
                                    line.append(row['port_status'])
                                    line.append(row['monitor_item'])

                                    data.append(line)

                                header = []

                                col_host = dict()
                                col_host['title'] = 'Host Name'
                                col_host['size'] = '12'

                                col_type = dict()
                                col_type['title'] = 'Type'
                                col_type['size'] = '8'

                                col_ip1 = dict()
                                col_ip1['title'] = 'Manage IP'
                                col_ip1['size'] = '12'

                                col_ip2 = dict()
                                col_ip2['title'] = 'Data IP'
                                col_ip2['size'] = '12'

                                col_status = dict()
                                col_status['title'] = 'State'
                                col_status['size'] = '10'

                                col_port = dict()
                                col_port['title'] = 'Port'
                                col_port['size'] = '10'

                                col_monitor = dict()
                                col_monitor['title'] = 'Monitor Item'
                                col_monitor['size'] = '14'

                                header.append(col_host)
                                header.append(col_type)
                                header.append(col_ip1)
                                header.append(col_ip2)
                                header.append(col_status)
                                header.append(col_port)
                                header.append(col_monitor)

                                cls.draw_grid(header, data)

                            print ''
                    elif param == 'port':
                        print('')
                        for sys in sorted_list:
                            print '[' + sys + ']'

                            sys_ret = result[sys]
                            if str(sys_ret).upper().endswith('FAIL'):
                                sys_ret = 'fail'
                                print sys_ret
                            else:
                                data = []

                                for row in sys_ret:
                                    is_first = True
                                    for port in row['port_list']:
                                        line = []

                                        if is_first:
                                            line.append(row['hostname'])
                                            is_first = False
                                        else:
                                            line.append('')

                                        line.append(port['port_name'])
                                        line.append(port['status'])

                                        data.append(line)

                                header = []

                                col_host = dict()
                                col_host['title'] = 'Hostname'
                                col_host['size'] = '12'

                                col_port = dict()
                                col_port['title'] = 'Port'
                                col_port['size'] = '14'

                                col_status = dict()
                                col_status['title'] = 'Status'
                                col_status['size'] = '6'

                                header.append(col_host)
                                header.append(col_port)
                                header.append(col_status)

                                cls.draw_grid(header, data)

                            print ''

                elif command == 'onos-conn':
                    if param == 'openflow':
                        print('')
                        for sys in sorted_list:
                            print '[' + sys + ']'

                            sys_ret = result[sys]
                            if str(sys_ret).upper().endswith('FAIL'):
                                sys_ret = 'fail'
                                print sys_ret
                            else:
                                data = []

                                for row in sys_ret:
                                    line = []

                                    line.append(row['hostname'])
                                    line.append(row['of_id'])
                                    line.append(row['available'])
                                    line.append(row['status'])
                                    line.append(row['role'])
                                    line.append(row['type'])
                                    line.append(row['monitor_item'])

                                    data.append(line)

                                header = []

                                col_host = dict()
                                col_host['title'] = 'Hostname'
                                col_host['size'] = '10'

                                col_id = dict()
                                col_id['title'] = 'of_id'
                                col_id['size'] = '20'

                                col_avail = dict()
                                col_avail['title'] = 'Available'
                                col_avail['size'] = '10'

                                col_status = dict()
                                col_status['title'] = 'Status'
                                col_status['size'] = '12'

                                col_role = dict()
                                col_role['title'] = 'Role'
                                col_role['size'] = '8'

                                col_type = dict()
                                col_type['title'] = 'Type'
                                col_type['size'] = '12'

                                col_monitor = dict()
                                col_monitor['title'] = 'monitor_item'
                                col_monitor['size'] = '12'

                                header.append(col_host)
                                header.append(col_id)
                                header.append(col_avail)
                                header.append(col_status)
                                header.append(col_role)
                                header.append(col_type)
                                header.append(col_monitor)

                                cls.draw_grid(header, data)

                            print ''

                    elif param == 'cluster':
                        print('')
                        for sys in sorted_list:
                            print '[' + sys + ']'

                            sys_ret = result[sys]
                            if str(sys_ret).upper().endswith('FAIL'):
                                sys_ret = 'fail'
                                print sys_ret
                            else:
                                data = []

                                for row in sys_ret:
                                    line = []

                                    line.append(row['id'])
                                    line.append(row['address'])
                                    line.append(row['status'])
                                    line.append(row['monitor_item'])

                                    data.append(line)

                                header = []

                                col_id = dict()
                                col_id['title'] = 'ID'
                                col_id['size'] = '12'

                                col_addr = dict()
                                col_addr['title'] = 'Address'
                                col_addr['size'] = '16'

                                col_state = dict()
                                col_state['title'] = 'State'
                                col_state['size'] = '6'

                                col_monitor = dict()
                                col_monitor['title'] = 'monitor_item'
                                col_monitor['size'] = '12'

                                header.append(col_id)
                                header.append(col_addr)
                                header.append(col_state)
                                header.append(col_monitor)

                                cls.draw_grid(header, data)

                            print ''

                elif command == 'gateway':
                    print('')
                    if param in ['docker', 'onosApp']:
                        for sys in sorted_list:
                            print '[' + sys + ']'

                            sys_ret = result[sys]
                            if str(sys_ret).upper().endswith('FAIL'):
                                sys_ret = 'fail'
                                print sys_ret
                            else:
                                data = []

                                for row in sys_ret:
                                    line = []

                                    line.append(row['name'])
                                    line.append(row['status'])

                                    data.append(line)

                                header = []

                                col_name = dict()
                                col_name['title'] = 'Name'
                                col_name['size'] = '14'

                                col_status = dict()
                                col_status['title'] = 'Status'
                                col_status['size'] = '8'

                                header.append(col_name)
                                header.append(col_status)

                                cls.draw_grid(header, data)

                            print ''
                    elif param == 'routingTable':
                        for sys in sorted_list:
                            print '[' + sys + ']'

                            sys_ret = result[sys]
                            if str(sys_ret).upper().endswith('FAIL'):
                                sys_ret = 'fail'
                                print sys_ret
                            else:
                                data = []

                                for row in sys_ret:
                                    line = []

                                    line.append(row['network'])
                                    line.append(row['next_hop'])

                                    data.append(line)

                                header = []

                                col_name = dict()
                                col_name['title'] = 'network'
                                col_name['size'] = '18'

                                col_hop = dict()
                                col_hop['title'] = 'next_hop'
                                col_hop['size'] = '18'

                                header.append(col_name)
                                header.append(col_hop)

                                cls.draw_grid(header, data)

                            print ''

                elif command == 'port-stat-vxlan':
                    print('')
                    for sys in sorted_list:
                        print '[' + sys + ']'

                        desc = ''
                        sys_ret = result[sys]
                        if str(sys_ret).upper().endswith('FAIL'):
                            sys_ret = 'fail'
                            print sys_ret
                        else:
                            print '   tx = ' + str(sys_ret['port_stat_vxlan']['tx']) + ', tx_drop = ' + str(sys_ret['port_stat_vxlan']['tx_drop']) \
                                  + ', tx_errs = ' + str(sys_ret['port_stat_vxlan']['tx_errs'])
                            print '   rx = ' + str(sys_ret['port_stat_vxlan']['rx']) + ', rx_drop = ' + \
                                  str(sys_ret['port_stat_vxlan']['rx_drop']) + ', rx_errs = ' + str(sys_ret['port_stat_vxlan']['rx_errs'])  + ', rx_min = ' + str(sys_ret['port_stat_vxlan']['minimum_rx'])

                            desc = '   * ' + sys_ret['description'] + '\n'

                            print('')
                    print desc

                elif command == 'traffic-gw':
                    print('')
                    for sys in sorted_list:
                        print '[' + sys + ']'

                        sys_ret = result[sys]
                        if str(sys_ret).upper().endswith('FAIL'):
                            sys_ret = 'fail'
                            print sys_ret
                        else:
                            print '   ratio = ' + sys_ret['ratio'] + '\n'

                elif command == 'xos-svc':
                    print('')
                    for sys in sorted_list:
                        print '[' + sys + ']'

                        sys_ret = result[sys]
                        if str(sys_ret).upper().endswith('FAIL'):
                            sys_ret = 'fail'
                            print sys_ret
                        else:
                            data = []

                            for row in sys_ret:
                                line = []

                                line.append(row['name'])
                                line.append(row['status'])
                                line.append(row['description'])

                                data.append(line)

                            header = []

                            col_name = dict()
                            col_name['title'] = 'Name'
                            col_name['size'] = '10'

                            col_status = dict()
                            col_status['title'] = 'Status'
                            col_status['size'] = '8'

                            col_desc = dict()
                            col_desc['title'] = 'Description'
                            col_desc['size'] = '30'

                            header.append(col_name)
                            header.append(col_status)
                            header.append(col_desc)

                            cls.draw_grid(header, data)

                        print ''

                elif command == 'synchronizer':
                    print('')
                    for sys in sorted_list:
                        print '[' + sys + ']'

                        sys_ret = result[sys]
                        if str(sys_ret).upper().endswith('FAIL'):
                            sys_ret = 'fail'
                            print sys_ret
                        else:
                            data = []

                            for row in sys_ret:
                                line = []

                                line.append(row['name'])
                                line.append(row['status'])
                                line.append(row['description'])
                                line.append(row['last_run_interval'])

                                data.append(line)

                            header = []

                            col_name = dict()
                            col_name['title'] = 'Name'
                            col_name['size'] = '20'

                            col_status = dict()
                            col_status['title'] = 'Status'
                            col_status['size'] = '8'

                            col_desc = dict()
                            col_desc['title'] = 'Description'
                            col_desc['size'] = '25'

                            col_interval = dict()
                            col_interval['title'] = 'Last Run'
                            col_interval['size'] = '10'

                            header.append(col_name)
                            header.append(col_status)
                            header.append(col_desc)
                            header.append(col_interval)

                            cls.draw_grid(header, data)

                        print ''

                elif command == 'swarm-svc':
                    if param == 'node':
                        print('')
                        for sys in sorted_list:
                            print '[' + sys + ']'

                            sys_ret = result[sys]
                            if str(sys_ret).upper().endswith('FAIL'):
                                sys_ret = 'fail'
                                print sys_ret
                            else:
                                data = []

                                for row in sys_ret:
                                    line = []
                                    line.append(row['hostname'])
                                    line.append(row['status'])
                                    line.append(row['availability'])
                                    line.append(row['manager'])

                                    data.append(line)

                                header = []

                                col_name = dict()
                                col_name['title'] = 'Hostname'
                                col_name['size'] = '10'

                                col_status = dict()
                                col_status['title'] = 'Status'
                                col_status['size'] = '8'

                                col_avail = dict()
                                col_avail['title'] = 'Availability'
                                col_avail['size'] = '13'

                                col_manager = dict()
                                col_manager['title'] = 'Manager'
                                col_manager['size'] = '8'

                                header.append(col_name)
                                header.append(col_status)
                                header.append(col_avail)
                                header.append(col_manager)

                                cls.draw_grid(header, data)

                            print ''

                else:
                    print('')
                    for sys in sorted_list:
                        sys_ret = result[sys]
                        if sys_ret.upper().endswith('FAIL'):
                            sys_ret = 'fail'

                        print '[' + sys + ']'

                        for line in sys_ret.splitlines():
                            print '   ' + line

                        print('')

            except:
                LOG.exception_err_write()
                print '[parser err] return = ' + str(result)

        except:
            LOG.exception_err_write()


    @staticmethod
    def draw_grid(header, data):
        RED = '\033[1;91m'
        BLUE = '\033[1;94m'
        OFF = '\033[0m'

        try:
            width = -1

            for col in header:
                width = width + int(col['size']) + 2

            print '+%s+' % ('-' * width).ljust(width)
            print '|',
            for col in header:
                cmd = '%' + col['size'] + 's|'
                title = str(col['title']).center(int(col['size']))
                print cmd % title,
            print ''

            print '+%s+' % ('-' * width).ljust(width)

            for line in data:
                print '|',
                i = 0
                for col in line:
                    if col == 'OK':
                        cmd = BLUE + '%' + header[i]['size'] + 's' + OFF + '|'
                    elif col == 'NOK' or col == 'NO':
                        cmd = RED + '%' + header[i]['size'] + 's' + OFF + '|'
                    else:
                        cmd = '%' + header[i]['size'] + 's|'

                    print cmd % col,
                    i = i + 1
                print ''

            print '+%s+' % ('-' * width).ljust(width)
        except:
            LOG.exception_err_write()


    @classmethod
    def send_rest(cls, cmd):
        auth = cls.get_auth()

        tmp = cmd.split(' ')
        param = ''
        system = ''

        if cmd.startswith('onos-shell ') or cmd.startswith('os-shell '):
            sys_name = tmp[1]
            param = cmd[len(tmp[0]) + 1 + len(sys_name) + 1:]
            system = sys_name
        else:
            system = cls.selected_sys

            if len(tmp) == 2:
                param = tmp[1]

        cmd = tmp[0]

        req_body = {'command': cmd, 'system': system, 'param': param}
        req_body_json = json.dumps(req_body)

        header = {'Content-Type': 'application/json', 'Authorization': base64.b64encode(auth)}

        cls.CLI_LOG.cli_log('---------------------------SEND CMD---------------------------')

        try:
            url = CONFIG.get_cmd_addr()
            cls.CLI_LOG.cli_log('URL = ' + url)
            cls.CLI_LOG.cli_log('AUTH = ' + auth)

            myResponse = requests.get(url, headers=header, data=req_body_json, timeout=CONFIG.get_rest_timeout())

            cls.CLI_LOG.cli_log('COMMAND = ' + cmd)
            cls.CLI_LOG.cli_log('SYSTEM = ' + cls.selected_sys)
            cls.CLI_LOG.cli_log('HEADER = ' + json.dumps(header, sort_keys=True, indent=4))
            cls.CLI_LOG.cli_log('BODY = ' + json.dumps(req_body, sort_keys=True, indent=4))

        except:
            # req timeout
            LOG.exception_err_write()
            return -1, None

        cls.CLI_LOG.cli_log('---------------------------RECV RES---------------------------')
        cls.CLI_LOG.cli_log('RESPONSE CODE = ' + str(myResponse.status_code))

        try:
            cls.CLI_LOG.cli_log(
                'BODY = ' + json.dumps(json.loads(myResponse.content.replace("\'", '"')), sort_keys=True, indent=4))
        except:
            cls.CLI_LOG.cli_log('BODY = ' + myResponse.content)

        return 1, myResponse


    @classmethod
    def send_regi(cls, type = 'regi'):
        auth = cls.get_auth()

        url = 'http://' + str(CONFIG.get_rest_ip()) + ':' + str(CONFIG.get_rest_port()) + '/event'

        req_body = {'url': url}
        req_body_json = json.dumps(req_body)

        header = {'Content-Type': 'application/json', 'Authorization': base64.b64encode(auth)}

        cls.CLI_LOG.cli_log('---------------------------SEND CMD---------------------------')

        try:
            if type == 'regi':
                url = CONFIG.get_regi_uri()
            else:
                url = CONFIG.get_unregi_uri()

            cls.CLI_LOG.cli_log('URL = ' + url)
            cls.CLI_LOG.cli_log('AUTH = ' + auth)

            myResponse = requests.get(url, headers=header, data=req_body_json, timeout=CONFIG.get_rest_timeout())

            cls.CLI_LOG.cli_log('HEADER = ' + json.dumps(header, sort_keys=True, indent=4))
            cls.CLI_LOG.cli_log('BODY = ' + json.dumps(req_body, sort_keys=True, indent=4))

        except:
            # req timeout
            LOG.exception_err_write()
            return False

        cls.CLI_LOG.cli_log('---------------------------RECV RES---------------------------')
        cls.CLI_LOG.cli_log('RESPONSE CODE = ' + str(myResponse.status_code))

        if myResponse.status_code == 200:
            result = json.loads(myResponse.content)

            if result['Result'] == 'SUCCESS':
                return True
            else:
                return False
        else:
            return False


    @classmethod
    def get_event_list(cls):
        auth = cls.get_auth()

        url = 'http://' + str(CONFIG.get_rest_ip()) + ':' + str(CONFIG.get_rest_port()) + '/event'

        req_body = {'url': url}
        req_body_json = json.dumps(req_body)

        header = {'Content-Type': 'application/json', 'Authorization': base64.b64encode(auth)}

        cls.CLI_LOG.cli_log('---------------------------SEND CMD---------------------------')

        try:
            url = CONFIG.get_event_list_uri()

            cls.CLI_LOG.cli_log('URL = ' + url)
            cls.CLI_LOG.cli_log('AUTH = ' + auth)

            myResponse = requests.get(url, headers=header, data=req_body_json, timeout=CONFIG.get_rest_timeout())

            cls.CLI_LOG.cli_log('HEADER = ' + json.dumps(header, sort_keys=True, indent=4))
            cls.CLI_LOG.cli_log('BODY = ' + json.dumps(req_body, sort_keys=True, indent=4))

        except:
            # req timeout
            LOG.exception_err_write()
            return False

        cls.CLI_LOG.cli_log('---------------------------RECV RES---------------------------')
        cls.CLI_LOG.cli_log('RESPONSE CODE = ' + str(myResponse.status_code))

        try:
            res = json.loads(myResponse.content.replace("\'", '"'))
            cls.CLI_LOG.cli_log(
                'BODY = ' + json.dumps(res, sort_keys=True, indent=4))

            cls.HISTORY_LOG.write_history("--- Current Event History Start ---")

            for line in res['Event list']:
                cls.HISTORY_LOG.write_history('[OCCUR_TIME : %s][%s][%s][%s] %s', line['time'], line['system'], line['item'],
                                           line['pre_grade'] + '->' + line['grade'], line['reason'])

            cls.HISTORY_LOG.write_history("--- Current Event History END ---")

        except:

            cls.CLI_LOG.cli_log('BODY = ' + myResponse.content)

        result = json.loads(myResponse.content)

        if myResponse.status_code == 200 and result['Result'] == 'SUCCESS':
            return True
        else:
            return False

    @staticmethod
    def get_auth():
        id = CONFIG.get_rest_id().strip()
        pw = CONFIG.get_rest_pw().strip()
        auth = id + ':' + pw

        return auth

    sys_command = 'system-status info'
    @classmethod
    def req_sys_info(cls):
        try:
            ret_code, myResponse = cls.send_rest(cls.sys_command)

            # rest timeout
            if ret_code == -1:
                return -1, myResponse
        except:
            LOG.exception_err_write()

        return myResponse.status_code, myResponse.content

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
            cls.cli_search_list.append('exit')
            cls.cli_search_list.append('sys')
            cls.cli_search_list.append('onos-shell')
            cls.cli_search_list.append('os-shell')
            cls.cli_search_list.append('monitoring-details')
            cls.cli_search_list.append('event-history')
            cls.cli_search_list.append('flow-trace')
            cls.cli_search_list.append('traffic-test')
            cls.cli_search_list.append('help')

            onos_list = []
            shell_list = []
            tmp_sys = []
            tmp_sys.append('all')
            cls.cli_validate_list.append('sys all')
            for sys_name in SYS.get_sys_list():
                tmp_sys.append(sys_name)
                cls.cli_validate_list.append('sys ' + sys_name)
                cls.cli_validate_list.append('os-shell ' + sys_name)

                if dict(SYS.sys_list[sys_name])['TYPE'] == 'ONOS':
                    onos_list.append(sys_name)

                shell_list.append(sys_name)

            cls.cli_search_list_sub['sys'] = tmp_sys
            cls.cli_search_list_sub['onos-shell'] = onos_list
            cls.cli_search_list_sub['os-shell'] = shell_list
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
