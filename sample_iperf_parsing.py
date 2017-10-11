#!/usr/bin/python

import time
import pexpect
import threading

from api.config import CONF
from api.sona_log import LOG

class VM:
    def __init__(self):
        self.id = ''
        self.passwd = ''
        self.ip = ''
        self.command = ''
        self.type = ''
        self.is_reverse = False

    def set_reverse(self, cli_command):
        if '-r' in cli_command or '-d' in cli_command:
            self.is_reverse = True

PROMPT = ['~# ', 'onos> ', '\$ ', '\# ', ':~$ ']

def run_test(vm_info, result_arr, index, total_timeout):
    try:
        ssh_options = '-o StrictHostKeyChecking=no ' \
                      '-o ConnectTimeout=' + str(CONF.ssh_conn()['ssh_req_timeout'])
        cmd = 'ssh %s %s@%s' % (ssh_options, vm_info.id, vm_info.ip)

        try:
            LOG.info('ssh_pexpect cmd = ' + cmd)
            ssh_conn = pexpect.spawn(cmd)

            try:
                rt_pw = ssh_conn.expect([pexpect.TIMEOUT, '[P|p]assword:', pexpect.EOF], timeout=CONF.ssh_conn()['ssh_req_timeout'])

                if rt_pw == 1:
                    ssh_conn.sendline(vm_info.passwd)
                    login_rt = ssh_conn.expect([pexpect.TIMEOUT, 'Login incorrect', '~# ', 'onos> ', '\$ ', '\# ', ':~$ '],
                                          timeout=CONF.ssh_conn()['ssh_req_timeout'])

                    if login_rt == 0 or login_rt == 1:
                        str_output = 'auth fail'
                    else:
                        ssh_conn.sendline(vm_info.command)
                        if vm_info.type == 'client':
                            command_rt = ssh_conn.expect([pexpect.TIMEOUT, '~# ', 'onos> ', '\$ ', '\# ', ':~$ '], timeout=total_timeout)
                            if command_rt == 0:
                                str_output = 'timeout'
                                ssh_conn.sendline('exit')
                                ssh_conn.close()
                                LOG.info(vm_info.ip + ' ' + str_output)
                            else:
                                str_output = iperfParser(ssh_conn.before)
                                ssh_conn.sendline('exit')
                                ssh_conn.close()
                                LOG.info(vm_info.ip + ' ' + str_output)
                        else:
                            command_rt = ssh_conn.expect([pexpect.TIMEOUT, '/sec'],
                                                  timeout=total_timeout)
                            if command_rt == 0:
                                str_output = 'timeout'
                                ssh_conn.sendline('exit')
                                ssh_conn.close()
                                LOG.info(vm_info.ip + ' ' + str_output)
                            else:
                                ret = ssh_conn.before
                                if vm_info.is_reverse:
                                    command_rt = ssh_conn.expect([pexpect.TIMEOUT, '/sec'],
                                                                 timeout=total_timeout)
                                    if command_rt != 0:
                                        ret = ret + ssh_conn.before

                                str_output = iperfParser(ret)
                                ssh_conn.sendline('exit')
                                ssh_conn.close()
                                LOG.info(vm_info.ip + ' ' + str_output)

                else:
                    str_output = 'auth fail'
            except:
                str_output = 'exception'
                ssh_conn.sendline('exit')
                ssh_conn.close()

        except:
            LOG.exception()
            str_output = 'exception 1'
    except:
        LOG.exception()
        str_output = 'exception 2'

    result_arr[index] = str_output.replace('\r\n', '\n')

def iperfParser(str):
    transfer = 'None'
    bandwidth = 'None'
    reverse_transfer = 'None'
    reverse_bandwidth = 'None'

    for line in str.splitlines():
        if ' 0.0-' in line:
            LOG.info('line = %s', line)
            t = line[line.find('sec') + len('sec'):line.find('GBytes')].strip()
            b = line[line.find('GBytes') + len('GBytes'):line.find('Gbits')].strip()

            if transfer == 'None':
                transfer = t
                bandwidth = b
            else:
                reverse_transfer = t
                reverse_bandwidth = b

    ret = 'transfer = ' + transfer + ', bandwidth = ' + bandwidth

    if reverse_transfer is not 'None':
        ret = ret + '\nreverse_transfer = ' + reverse_transfer + ', reverse_bandwidth = ' + reverse_bandwidth

    return ret


if __name__ == "__main__":
    result_arr = []
    result_arr.append('timeout')
    result_arr.append('timeout')

    timeout = 30

    server_info = VM()
    server_info.ip = '10.10.2.51'
    server_info.id = 'hs'
    server_info.passwd = 'hs'
    server_info.command = 'iperf -s'
    server_info.type = 'server'

    client_info = VM()
    client_info.ip = '10.20.0.91'
    client_info.id = 'root'
    client_info.passwd = 'root'
    client_info.command = 'iperf -c 10.20.0.99 -d'
    client_info.type = 'client'

    server_info.set_reverse(client_info.command)
    client_info.set_reverse(client_info.command)

    # start server
    run_thread = threading.Thread(target=run_test, args=(server_info, result_arr, 0, timeout))
    run_thread.daemon = False
    run_thread.start()

    time.sleep(1)

    # start client
    run_thread = threading.Thread(target=run_test, args=(client_info, result_arr, 1, timeout))
    run_thread.daemon = False
    run_thread.start()

    wait_time = timeout

    while wait_time > 0:
        find_timeout = False
        i = 0
        while i < len(result_arr):
            if result_arr[i] == 'timeout':
                find_timeout = True
            i = i + 1

        if find_timeout:
            time.sleep(1)
        else:
            break

        wait_time = wait_time - 1

    i = 0
    while i < len(result_arr):
        print(result_arr[i])
        i = i + 1

    pass



