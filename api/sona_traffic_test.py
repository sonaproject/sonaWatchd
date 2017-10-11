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
        self.command = ''
        self.hostname = ''
        self.compute_ip = ''
        self.type = ''
        self.is_reverse = False
        self.floating_ip = ''
        self.id = 'root'
        self.passwd = 'root'

    def set_reverse(self, cli_command):
        if '-r' in cli_command or '-d' in cli_command:
            self.is_reverse = True

def create_instance(server_options, client_options):
    server_id = make_vm(server_options)
    client_id = make_vm(client_options)

    return server_id, client_id

def make_command(server_options, client_options, command, server_info, client_info):
    svr_cmd = command + ' -s ' + convert_command(server_options)
    cli_cmd = command + ' -c ' + convert_command(client_options)

    server_info.command = svr_cmd
    client_info.command = cli_cmd

    server_info.type = 'server'
    client_info.type = 'client'

    server_info.set_reverse(client_info.command)
    client_info.set_reverse(client_info.command)

def traffic_test_new(server_info, client_info, condition_json):
    trace_result = []

    result_arr = []
    result_arr.append('timeout')

    timeout = 30
    if dict(condition_json).has_key('timeout'):
        timeout = condition_json['timeout']

    # start client
    run_thread = threading.Thread(target=run_test, args=(client_info, result_arr, 0, timeout))
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

    image = nova.images.find(name=image)
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

        if vm_info.type == 'client':
            floatingip_list = nova.floating_ips.list()

            extra_floatingip = ''
            for a in floatingip_list:
                if not a.fixed_ip:
                    extra_floatingip = a.ip
                    break

            if not extra_floatingip:
                extra_floatingip = nova.floating_ips.create('ext-net').ip

            LOG.info('floating ip = ' + extra_floatingip)

            time.sleep(1)
            instance_rst.add_floating_ip(extra_floatingip)

            vm_info.floating_ip = extra_floatingip

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