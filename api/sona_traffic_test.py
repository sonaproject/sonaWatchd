# Copyright (c) 2017 by Telcoware kimjt
# All Rights Reserved.
# SONA Monitoring Solutions.

import time
import random
import json
import numpy

from threading import Thread
from Queue import Queue
from sona_log import LOG
from config import CONF
from sbapi import SshCommand
from novaclient import client


def create_instance(server_options, client_options):
    server_instance = client_instance = None

    image_name = CONF.openstack()['image']
    flavor_name = CONF.openstack()['flavor']
    securitygroups = CONF.openstack()['security_groups']
    keypair = CONF.openstack()['keypair_name']

    # TODO add exception for connection
    nova_credentials = client.Client(CONF.openstack()['version'],
                                     CONF.openstack()['username'],
                                     CONF.openstack()['api_key'],
                                     CONF.openstack()['project_id'],
                                     CONF.openstack()['auth_url'])

    image = nova_credentials.images.find(name=image_name)
    flavor = nova_credentials.flavors.find(name=flavor_name)
    hypervisors = nova_credentials.hypervisors.list()

    onos_ip = CONF.onos()['list'].pop().split(':')[-1]
    dpid2ip = {c[2]: c[3] for c in [(" ".join(l.split()).split(" "))
               for l in SshCommand.onos_ssh_exec(onos_ip, 'openstack-nodes | grep COMPUTE').splitlines()]}

    def get_zone(dpid):
        if dpid:
            for h in hypervisors:
                if h.host_ip == dpid2ip[dpid]:
                    return 'nova:' + h.service['host']
        else:
            return "nova"

    # TODO: when no network_id, choice a network excepted external netwrok
    # network_id = server_options['network_id'] if server_options['network_id'] \
    #     else random.choice(nova.networks.list()).id
    # network_list = nova_credentials.networks.list()
    # target_network.append(str(network_list[-1]).split(':')[1][:-1].strip())

    # Create server VM info
    vm_name = 'tperf_server_vm_' + str(random.randrange(10000, 20000))
    LOG.info('[server] - vmname = %s', vm_name)
    LOG.info('         | image = %s', image)
    LOG.info('         | flavor = %s', flavor)
    LOG.info('         | availability_zone = %s', get_zone(server_options['vm_location']))
    LOG.info('         | nics = %s', server_options['network_id'])
    LOG.info('         | security_groups = %s', securitygroups)
    LOG.info('         | key_pair = %s', keypair)

    nova_credentials.servers.create(name=vm_name,
                                    image=image,
                                    flavor=flavor,
                                    availability_zone=get_zone(server_options['vm_location']),
                                    nics=[{'net-id': server_options['network_id']}],
                                    security_groups=securitygroups,
                                    key_name=keypair)
    for i in range(20):
        time.sleep(1)
        server_instance = nova_credentials.servers.list(search_opts={'name': vm_name})[0]
        # server_instance = nova_credentials.servers.list(search_opts={'name': 'tperf_server_vm_17693'})[0]
        if server_instance.__dict__['addresses']:
            LOG.info("[Server VM created and ACTIVE] - %s", server_instance)
            break

    # Create client VM info
    vm_name = 'tperf_client_vm_' + str(random.randrange(10000, 20000))
    LOG.info('[client] - vmname = %s', vm_name)
    LOG.info('         | image = %s', image)
    LOG.info('         | flavor = %s', flavor)
    LOG.info('         | availability_zone = %s', get_zone(client_options['vm_location']))
    LOG.info('         | nics = %s', client_options['network_id'])
    LOG.info('         | security_groups = %s', securitygroups)
    LOG.info('         | key_pair = %s', keypair)

    nova_credentials.servers.create(name=vm_name,
                                    image=image,
                                    flavor=flavor,
                                    availability_zone=get_zone(client_options['vm_location']),
                                    nics=[{'net-id': client_options['network_id']}],
                                    security_groups=securitygroups,
                                    key_name=keypair)

    client_floatingip = get_floatingip(nova_credentials)
    # client_floatingip = '172.27.0.179'

    for i in range(20):
        time.sleep(1)
        client_instance = nova_credentials.servers.list(search_opts={'name': vm_name})[0]
        # client_instance = nova_credentials.servers.list(search_opts={'name': 'tperf_client_vm_15442'})[0]
        if client_instance.__dict__['addresses']:
            LOG.info("[Client VM created and ACTIVE] - %s", client_instance)
            nova_credentials.servers.add_floating_ip(client_instance, client_floatingip.ip)
            LOG.info("[Floating_IP Assignment] to Client ---")
            break

    return server_instance, client_instance, client_floatingip


def get_floatingip(nova_credentials):
    for network in nova_credentials.networks.list():
        try:
            new_floatingip = nova_credentials.floating_ips.create(pool=network.label)
            if new_floatingip:
                LOG.info("[Create Floating_IP] Success %s", new_floatingip.ip)
                return new_floatingip
        except client.exceptions.NotFound:
            LOG.info("[Create Floating_IP] Fail from %s network", network.label)


def tperf_command_exec(server_ip, client_floatingip, tperf_json_options):
    tperf_cmd_options = ""
    tperf_command = 'iperf3 -c ' + str(server_ip) + ' --json'
    tperf_run_count = 1
    # iperf) udp: 5230~5238, tcp: 5220~5280 || iperf3) 5300~5308
    tperf_server_port = 5300
    tperf_output = [None]
    tperf_threads = [None]

    if tperf_json_options:
        if 'parallel' in tperf_json_options.keys():
            tperf_run_count = 8 if tperf_json_options['parallel'] > 8 else tperf_json_options['parallel']
            tperf_output = [None] * tperf_run_count
            tperf_threads = [None] * tperf_run_count

        if tperf_json_options['protocol_type'] == 'udp':
            tperf_cmd_options = tperf_cmd_options + ' -u'
        else:
            # TODO protocol tcp suppert
            tperf_cmd_options = tperf_cmd_options + ' -u -Z'

        if 'block_size' in tperf_json_options.keys():
            # vxlan packet header size:  96
            header = 0
            if tperf_json_options['block_size'] > header:
                tperf_cmd_options = tperf_cmd_options + ' -l ' + str(tperf_json_options['block_size'] - header)
            else:
                tperf_cmd_options = tperf_cmd_options + ' -l ' + str(tperf_json_options['block_size'])

        if 'transmit_time' in tperf_json_options.keys():
            tperf_cmd_options = tperf_cmd_options \
                                + ' -t ' + str(tperf_json_options['transmit_time']) \
                                + ' -i ' + str(tperf_json_options['transmit_time'])

        if 'bandwidth' in tperf_json_options.keys():
            tperf_cmd_options = tperf_cmd_options + ' -b ' + str(tperf_json_options['bandwidth'] / tperf_run_count)

        tperf_command = tperf_command + tperf_cmd_options

    if server_vm_check(server_ip, client_floatingip):
        for thread_i in range(tperf_run_count):
            cmd = tperf_command + ' -p ' + str(tperf_server_port + thread_i)
            tperf_threads[thread_i] = Thread(target=tperf_cmd_exec,
                                             args=(client_floatingip, cmd,
                                                   tperf_json_options['transmit_time'], tperf_output, thread_i))
            tperf_threads[thread_i].start()

        for thread_i in range(tperf_run_count):
            tperf_threads[thread_i].join()

    else:
        return {'result': 'FAIL', 'fail_reason': 'Client SSH Connection fail or Server VM network fail'}

    return tperf3_output_parse(tperf_output)


def tperf_cmd_exec(client_floatingip, tperf_command, transmit_time, tperf_output, thread_index):
    for i in range(10):
        tperf_output[thread_index] = SshCommand.ssh_tperf_exec(CONF.openstack()['key_file'],
                                                               CONF.openstack()['tperf_vm_username'],
                                                               client_floatingip,
                                                               tperf_command,
                                                               timeout=int(transmit_time) + 5)
        if tperf_output[thread_index] == 'fail':
            time.sleep(2)
        else:
            break


def server_vm_check(server_ip, client_floatingip):
    for i in range(20):
        check_result = SshCommand.ssh_tperf_exec(CONF.openstack()['key_file'],
                                                 CONF.openstack()['tperf_vm_username'],
                                                 client_floatingip,
                                                 'ping -c 1 ' + server_ip + ' | grep transmitted',
                                                 timeout=2)
        if ' 0% packet loss' in check_result.split(','):
            return True
        else:
            LOG.error('[Server Network Check Fail and Retry %d', i)
            time.sleep(1)
    return False


def tperf3_output_parse(tperf_out_list):
    parse_result = {'test_options': {}, 'test_result': {}, 'cpu_utilization_percent': {}}
    tout_protocol_l = list()
    tout_num_streams_l = list()
    tout_blksize_l = list()
    tout_duration_l = list()

    tout_start_l = list()
    tout_end_l = list()
    tout_seconds_l = list()
    tout_bytes_l = list()
    tout_bps_l = list()
    tout_jitter_l = list()
    tout_lost_packet_l = list()
    tout_packet_l = list()
    tout_lost_percent_l = list()

    tout_client_cpu_l = list()
    tout_server_cpu_l = list()

    for i in range(len(tperf_out_list)):
        if tperf_out_list[i] == 'fail':
            return {'result': 'FAIL', 'fail_reason': 'Tperf command run fail on Client VM'}
        try:
            tperf_out_list[i] = json.loads(' '.join(str(tperf_out_list[i]).split()))

            tout_protocol_l.append(tperf_out_list[i]['start']['test_start']['protocol'])
            tout_num_streams_l.append(tperf_out_list[i]['start']['test_start']['num_streams'])
            tout_blksize_l.append(tperf_out_list[i]['start']['test_start']['blksize'])
            tout_duration_l.append(tperf_out_list[i]['start']['test_start']['duration'])

            tout_start_l.append(float(tperf_out_list[i]['end']['sum']['start']))
            tout_end_l.append(float(tperf_out_list[i]['end']['sum']['end']))
            tout_seconds_l.append(float(tperf_out_list[i]['end']['sum']['seconds']))
            tout_bytes_l.append(float(tperf_out_list[i]['end']['sum']['bytes']))
            tout_bps_l.append(float(tperf_out_list[i]['end']['sum']['bits_per_second']))
            tout_jitter_l.append(float(tperf_out_list[i]['end']['sum']['jitter_ms']))
            tout_lost_packet_l.append(float(tperf_out_list[i]['end']['sum']['lost_packets']))
            tout_packet_l.append(float(tperf_out_list[i]['end']['sum']['packets']))
            tout_lost_percent_l.append(float(tperf_out_list[i]['end']['sum']['lost_percent']))

            tout_client_cpu_l.append(float(tperf_out_list[i]['end']['cpu_utilization_percent']['host_total']))
            tout_server_cpu_l.append(float(tperf_out_list[i]['end']['cpu_utilization_percent']['remote_total']))
        except:
            LOG.exception()
            return {'result': 'FAIL', 'fail_reason': ''}

    parse_result['test_options'].update({'protocol': tout_protocol_l[0]})
    parse_result['test_options'].update({'parallel': sum(tout_num_streams_l)})
    parse_result['test_options'].update({'blksize': tout_blksize_l[0]})
    parse_result['test_options'].update({'duration': tout_duration_l[0]})
    parse_result['test_options'].update({'reverse': tperf_out_list[0]['start']['test_start']['reverse']})

    parse_result['test_result'].update({'start': sum(tout_start_l)/len(tperf_out_list)})
    parse_result['test_result'].update({'end': sum(tout_end_l)/len(tperf_out_list)})
    parse_result['test_result'].update({'seconds': sum(tout_seconds_l)/len(tperf_out_list)})
    parse_result['test_result'].update({'bytes': sum(tout_bytes_l)})
    parse_result['test_result'].update({'bits_per_second': sum(tout_bps_l)})
    parse_result['test_result'].update({'jitter_ms': sum(tout_jitter_l)/len(tperf_out_list)})
    parse_result['test_result'].update({'lost_packets': sum(tout_lost_packet_l)})
    parse_result['test_result'].update({'packets': sum(tout_packet_l)})
    parse_result['test_result'].update({'lost_percent': sum(tout_lost_percent_l)/len(tperf_out_list)})

    parse_result['cpu_utilization_percent'].update({'client_total': sum(tout_client_cpu_l)/len(tperf_out_list)})
    parse_result['cpu_utilization_percent'].update({'server_total': sum(tout_server_cpu_l)/len(tperf_out_list)})

    parse_result['result'] = 'SUCCESS'

    return parse_result


def delete_test_instance(server_vm, client_vm, client_floatingip):
    try:
        nova_credentials = client.Client(CONF.openstack()['version'],
                                         CONF.openstack()['username'],
                                         CONF.openstack()['api_key'],
                                         CONF.openstack()['project_id'],
                                         CONF.openstack()['auth_url'])

        nova_credentials.floating_ips.delete(client_floatingip)
        LOG.info('[Tperf Test] Client floatingip Deleted --- ')

        for vm in [server_vm, client_vm]:
            if vm:
                nova_credentials.servers.delete(vm)
        LOG.info('[Tperf Test] Server and Client instance Deleted] --- ')

    except:
        LOG.exception()

