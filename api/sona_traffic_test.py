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
        self.type = ''
        self.is_reverse = False
        # for using virsh console
        self.id = ''
        self.compute_ip = ''
        # for using iperf/iperf3
        self.local_ip = ''
        self.floating_ip = ''
        self.vm_id = 'root'
        self.vm_passwd = 'root'

    def set_reverse(self, cli_command):
        if '-r' in cli_command or '-d' in cli_command:
            self.is_reverse = True

def create_instance(server_options, client_options):
    server_id = make_vm(server_options, 'server')
    client_id = make_vm(client_options, 'client')

    time.sleep(10)

    return server_id, client_id

def make_command(server_options, client_options, command, server_info, client_info):
    svr_cmd = command + ' -s ' + convert_command(server_options, command)
    cli_cmd = command + ' -c ' + server_info.local_ip + ' ' + convert_command(client_options, command)

    server_info.command = svr_cmd
    client_info.command = cli_cmd

    server_info.type = 'server'
    client_info.type = 'client'

    server_info.set_reverse(client_info.command)
    client_info.set_reverse(client_info.command)

def traffic_test_new(server_info, client_info, condition_json):
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

    return True, result_arr[0]


PROMPT = ['~# ', 'onos> ', '\$ ', '\# ', ':~$ ']

def run_test(vm_info, result_arr, index, total_timeout):
    try:
        ssh_options = '-o StrictHostKeyChecking=no ' \
                      '-o ConnectTimeout=' + str(CONF.ssh_conn()['ssh_req_timeout'])
        cmd = 'ssh %s %s@%s' % (ssh_options, vm_info.vm_id, vm_info.floating_ip)

        try:
            LOG.info('ssh_pexpect cmd = ' + cmd)
            ssh_conn = pexpect.spawn(cmd)

            try:
                rt_pw = ssh_conn.expect([pexpect.TIMEOUT, '[P|p]assword:', pexpect.EOF], timeout=CONF.ssh_conn()['ssh_req_timeout'])

                if rt_pw == 0:
                    str_output = 'ssh timeout'
                elif rt_pw == 1:
                    ssh_conn.sendline(vm_info.vm_passwd)
                    login_rt = ssh_conn.expect([pexpect.TIMEOUT, 'Login incorrect', '~# ', 'onos> ', '\$ ', '\# ', ':~$ '],
                                          timeout=CONF.ssh_conn()['ssh_req_timeout'])

                    if login_rt in [0, 1]:
                        str_output = 'auth fail'
                    else:
                        ssh_conn.sendline(vm_info.command)

                        command_rt = ssh_conn.expect(['connect failed: Connection refused', pexpect.TIMEOUT, '~# ', 'onos> ', '\$ ', '\# ', ':~$ '], timeout=total_timeout)
                        if command_rt == 0:
                            LOG.info('connection refused = [%s]', ssh_conn.before)
                            ssh_conn.sendline('exit')
                            ssh_conn.close()
                            str_output = 'connection refused'
                        elif command_rt == 1:
                            str_output = 'timeout'
                            ssh_conn.sendline('exit')
                            ssh_conn.close()
                            LOG.info(vm_info.local_ip + ' ' + str_output)
                        else:
                            LOG.info('go parser = [%s]', ssh_conn.before)
                            str_output = iperfParser(ssh_conn.before, vm_info.command)
                            ssh_conn.sendline('exit')
                            ssh_conn.close()
                            LOG.info(vm_info.local_ip + ' ' + str(str_output))

            except:
                LOG.exception()
                str_output = 'exception'
                ssh_conn.sendline('exit')
                ssh_conn.close()

        except:
            LOG.exception()
            str_output = 'exception 1'
    except:
        LOG.exception()
        str_output = 'exception 2'

    result_arr[index] = str(str_output).replace('\r\n', '\n')


def iperfParser(str, command):
    result = dict()

    transfer = 'None'
    bandwidth = 'None'
    reverse_transfer = 'None'
    reverse_bandwidth = 'None'

    if 'iperf3' in command:
        key = 'sender'
    else:
        key = ' 0.0-'


    for line in str.splitlines():
        if key in line:
            LOG.info('line = %s', line)
            t = line[line.find('sec') + len('sec'):line.find('GBytes')].strip()
            b = line[line.find('GBytes') + len('GBytes'):line.find('Gbits')].strip()

            if transfer == 'None':
                transfer = t
                bandwidth = b
            else:
                reverse_transfer = t
                reverse_bandwidth = b

    result['transfer'] = transfer
    result['bandwidth'] = bandwidth

    if reverse_transfer is not 'None':
        result['reverse_transfer'] = reverse_transfer
        result['reverse_bandwidth'] = reverse_bandwidth

    return result


def convert_command(options, command):
    str_option = ''

    if options is not None:
        if dict(options).has_key('port'):
            str_option = str_option + '-p ' + options['port'] + ' '
        else:
            if command == 'iperf':
                if dict(options).has_key('udp'):
                    str_option = str_option + '-p 5230'
                else:
                    str_option = str_option + '-p 5220'
            elif command == 'iperf3':
                str_option = str_option + '-p 5300'

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

def del_vm(name):
    version = CONF.openstack()['version']
    username = CONF.openstack()['username']
    api_key = CONF.openstack()['api_key']
    project_id = CONF.openstack()['project_id']
    auth_url = CONF.openstack()['auth_url']

    nova = client.Client(version, username, api_key, project_id, auth_url)
    instance_ret = nova.servers.list(search_opts={'name': name})

    for ins in instance_ret:
        nova.servers.delete(ins)

def make_vm(options, vm_type = 'client'):
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

    zone = default_zone

    vm_name = 'test' + str(random.randrange(10000, 20000))

    vm_info.name = vm_name
    vm_info.type = vm_type

    if not options is None:
        if dict(options).has_key('compute_node_dpid'):
            target_compute_node = get_hostname(vm_info, options['compute_node_dpid'])
            zone = default_zone + ':' + target_compute_node

        if dict(options).has_key('networks'):
            target_networks = options['networks']

    network_list = []
    for net in target_networks:
        network_list.append({'net-id': nova.networks.find(label=net).id})

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

    status = ''
    count = 0
    while not status == 'ACTIVE':
        instance_for_ip = nova.servers.list(search_opts={'name': vm_name})
        instance_for_ip = instance_for_ip[0].__dict__
        status = instance_for_ip['status']
        time.sleep(1)
        count = count + 1

        # timeout
        if count > 10:
            return None

    if vm_name in str(instance_rst):
        instance = nova.servers.find(name=vm_name)
        vm_info.id = instance.id

        vm_info.local_ip = instance_for_ip['addresses'][target_networks[0]][0]['addr']

        if vm_info.type == 'client':
            '''
            floatingip_list = nova.floating_ips.list()

            extra_floatingip = ''
            for a in floatingip_list:
                if not a.fixed_ip:
                    extra_floatingip = a.ip
                    break

            if not extra_floatingip:
            '''
            extra_floatingip = nova.floating_ips.create('ext-net').ip

            LOG.info('floating ip = ' + extra_floatingip)

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