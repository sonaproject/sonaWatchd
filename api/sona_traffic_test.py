import time
import random
import pexpect
import threading

from sona_log import LOG
from config import CONF
from sbapi import SshCommand

from novaclient import client

class VM:
    def __init__(self):
        self.name = ''
        self.id = ''
        self.command = ''
        self.hostname = ''
        self.compute_ip = ''

def create_instance(server_options, client_options):
    server_id = make_vm(server_options)
    client_id = make_vm(client_options)

    return server_id, client_id

def make_command(server_options, client_options, command, server_info, client_info):
    svr_cmd = command + ' -s ' + convert_command(server_options)
    cli_cmd = command + ' -c ' + convert_command(client_options)

    server_info.command = svr_cmd
    client_info.command = cli_cmd

def traffic_test_new(server_info, client_info, condition_json):
    trace_result = []

    result_arr = []
    result_arr.append('timeout')
    result_arr.append('timeout')

    timeout = 30
    if dict(condition_json).has_key('timeout'):
        timeout = condition_json['timeout']

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
        trace_result.append(result_arr[i])
        i = i + 1

    return True, trace_result


PROMPT = ['~# ', 'onos> ', '\$ ', '\# ', ':~$ ']

def run_test(vm_info, result_arr, index, total_timeout):
    try:
        ins_id = vm_info.id
        user = 'cirros'
        pw = 'cubswin:)'
        command = vm_info.command
        ip = vm_info.compute_ip

        node_id = CONF.openstack()['account'].split(':')[0]

        ssh_options = '-o StrictHostKeyChecking=no ' \
                      '-o ConnectTimeout=' + str(CONF.ssh_conn()['ssh_req_timeout'])
        cmd = 'ssh %s %s@%s' % (ssh_options, node_id, ip)

        try:
            LOG.info('ssh_pexpect cmd = ' + cmd)
            ssh_conn = pexpect.spawn(cmd)
            rt1 = ssh_conn.expect(PROMPT, timeout=CONF.ssh_conn()['ssh_req_timeout'])

            if rt1 == 0:
                cmd = 'virsh console ' + ins_id

                LOG.info('ssh_pexpect cmd = ' + cmd)
                ssh_conn.sendline(cmd)
                rt2 = ssh_conn.expect([pexpect.TIMEOUT, 'Escape character is', 'error:', pexpect.EOF], timeout=CONF.ssh_conn()['ssh_req_timeout'])

                if rt2 == 0:
                    str_output = cmd + ' timeout'
                elif rt2 == 1:
                    ssh_conn.sendline('\n')
                    try:
                        rt3 = ssh_conn.expect(['login: ', pexpect.EOF, pexpect.TIMEOUT], timeout=CONF.ssh_conn()['ssh_req_timeout'])

                        LOG.info('rt3 = ' + str(rt3))

                        if rt3 == 2:
                            str_output = 'Permission denied'
                        else:
                            ssh_conn.sendline(user)
                            rt_pw = ssh_conn.expect([pexpect.TIMEOUT, '[P|p]assword:', pexpect.EOF], timeout=CONF.ssh_conn()['ssh_req_timeout'])

                            if rt_pw == 1:
                                ssh_conn.sendline(pw)
                                rt4 = ssh_conn.expect([pexpect.TIMEOUT, 'Login incorrect', '~# ', 'onos> ', '\$ ', '\# ', ':~$ '],
                                                      timeout=CONF.ssh_conn()['ssh_req_timeout'])

                                LOG.info('rt4 = ' + str(rt4))
                                if rt4 == 0 or rt4 == 1:
                                    str_output = 'auth fail'
                                else:
                                    ssh_conn.sendline(command)
                                    rt5 = ssh_conn.expect([pexpect.TIMEOUT, '~# ', 'onos> ', '\$ ', '\# ', ':~$ '], timeout=total_timeout)
                                    if rt5 == 0:
                                        str_output = 'timeout'
                                        ssh_conn.sendline('exit')
                                        ssh_conn.close()
                                    else:
                                        str_output = ssh_conn.before
                                        ssh_conn.sendline('exit')
                                        ssh_conn.close()
                            else:
                                str_output = 'auth fail'
                    except:
                        str_output = 'exception'
                        ssh_conn.sendline('exit')
                        ssh_conn.close()
                elif rt2 == 2:
                    result = {'command_result': 'virsh console error'}
                    result_arr[index] = result
                    return

                else:
                    str_output = 'connection fail'

        except:
            LOG.exception()
            str_output = 'exception 1'
    except:
        LOG.exception()
        str_output = 'exception 2'

    result_arr[index] = str_output.replace('\r\n', '\n')

def convert_command(options):
    str_option = ''

    if options is not None:
        if dict(options).has_key('port'):
            str_option = str_option + '-p ' + options['port'] + ' '

        if dict(options).has_key('udp'):
            if options['udp'] == 'UDP':
                str_option = str_option + '-u '

        if dict(options).has_key('tcp_window_size'):
            str_option = str_option + '-w ' + options['tcp_window_size'] + ' '

        if dict(options).has_key('interval'):
            str_option = str_option + '-i ' + options['interval'] + ' '

        if dict(options).has_key('time'):
            str_option = str_option + '-t ' + options['time'] + ' '

        if dict(options).has_key('parallel'):
            str_option = str_option + '-P' + options['parallel'] + ' '

        if dict(options).has_key('type'):
            if options['type'] == 'dualtest':
                str_option = str_option + '-d '
            elif options['type'] == 'tradeoff':
                str_option = str_option + '-r '

    return str_option


def make_vm(options):
    vm_info = VM()
    target_networks = []

    version = CONF.openstack()['version']
    username = CONF.openstack()['username']
    api_key = CONF.openstack()['api_key']
    project_id = CONF.openstack()['project_id']
    auth_url = CONF.openstack()['auth_url']
    image = CONF.openstack()['image']
    flavor = CONF.openstack()['flavor']
    default_zone = CONF.openstack()['zone']
    securitygroups = CONF.openstack()['security_groups']

    nova = client.Client(version, username, api_key, project_id, auth_url)

    network_list = nova.networks.list()
    target_networks.append(str(network_list[-1]).split(':')[1][:-1].strip())

    target_compute_node = get_hostname(vm_info)
    zone = default_zone + ':' + target_compute_node

    vm_name = 'test' + str(random.randrange(10000, 20000))

    vm_info.name = vm_name

    if not options is None:
        if dict(options).has_key('compute_node_dpid'):
            target_compute_node = get_hostname(vm_info, options['compute_node_dpid'])
            zone = default_zone + ':' + target_compute_node

        if dict(options).has_key('networks'):
            target_networks = options['networks']

    network_list = []
    for net in target_networks:
        network_list.append({'net-id': nova.networks.find(label=net).id})

    image = nova.images.find(name=image)
    flavor = nova.flavors.find(name=flavor)

    # create instance
    LOG.info('vmname = %s', vm_name)
    LOG.info('image = %s', image)
    LOG.info('flavor = %s', flavor)
    LOG.info('availability_zone = %s', zone)
    LOG.info('nics = %s', str(network_list))
    LOG.info('security_groups = %s', str(securitygroups))

    instance_rst = nova.servers.create(name=vm_name,
                                       image=image,
                                       flavor=flavor,
                                       availability_zone=zone,
                                       nics=network_list,
                                       security_groups=securitygroups)

    if vm_name in str(instance_rst):
        instance_id = nova.servers.find(name=vm_name).id
        vm_info.id = instance_id

        return vm_info

    return None


def get_compute_ip():
    return str(list(CONF.openstack()['compute_list']).pop()).split(':')[-1]

def get_onos_ip():
    return str(list(CONF.onos()['list']).pop()).split(':')[-1]

def get_hostname(vm_info, dpid = 'default'):
    if dpid == 'default':
        hostname = SshCommand.ssh_exec(CONF.openstack()['account'].split(':')[0], get_compute_ip(), 'hostname')
        vm_info.compute_ip = get_compute_ip()
    else:
        onos_ssh_result = SshCommand.onos_ssh_exec(get_onos_ip(), 'openstack-nodes | grep ' + dpid)

        node_info = " ".join(str(onos_ssh_result).split())

        tmp = node_info.split(' ')

        if tmp[3].startswith('of:'):
            target_ip = tmp[4]
        else:
            target_ip = tmp[3]

        hostname = SshCommand.ssh_exec(CONF.openstack()['account'].split(':')[0], target_ip, 'hostname')
        vm_info.compute_ip = target_ip

    vm_info.hostname = hostname.strip()

    return vm_info.hostname