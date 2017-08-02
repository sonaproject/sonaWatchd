# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

from sona_log import LOG
import re
from config import CONF
from sbapi import SshCommand


class Command:
    ONOS_SUBNET = 'openstack-networks'
    ONOS_HOST = 'hosts'
    ONOS_DEVICE = 'devices'
    ONOS_FLOATINGIP = 'openstack-floatingips'

class Conditions:
    def __init__(self):
        self.ether_type = ''
        self.dest_macaddr = ''
        self.src_ip = ''
        self.dest_ip = ''
        self.inport = ''
        self.vxlan_id = ''
        self.vlan_id = ''
        self.src_location = ''
        self.dest_location = ''
        self.reverse = False
        self.trace_net_type = ''


class Topology:
    def __init__(self):
        self.subnets = self.get_subnets(self.get_onos_ip())
        self.floatingips = self.get_floatingips(self.get_onos_ip())
        self.devices = []

    def get_onos_ip(self):
        return str(list(CONF.onos()['list']).pop()).split(':')[-1]

    def get_subnets(self, onos_ip):
        onos_ssh_result = SshCommand.onos_ssh_exec(onos_ip, Command.ONOS_SUBNET)
        subnets = re.findall(r'[0-9]+(?:\.[0-9]+){3}(?:/\d\d)', onos_ssh_result)
        return subnets

    def get_floatingips(self, onos_ip):
        onos_ssh_result = SshCommand.onos_ssh_exec(onos_ip, Command.ONOS_FLOATINGIP)
        floatingips = re.findall(r'[0-9]+(?:\.[0-9]+){3}(?: +)(?:[0-9]+(?:\.[0-9]+){3})', onos_ssh_result)

        floatingip_set = {}
        for l in floatingips:
            floatingip_set[l.split(' ')[0]] = l.split(' ')[-1]

        return floatingip_set

    def get_devices(self):
        pass


def flow_trace(condition_json):
    trace_result = {}

    trace_condition = check_condition(condition_json)

    # TODO: get_openstack_nodes()
    # TODO: get_hosts()
    # TODO: get_subnets()
    sona_topology = Topology()

    LOG.info('  kjt    %s', sona_topology.subnets)
    LOG.info('  kjt    %s', sona_topology.floatingips)
    return

    # # TODO up direction trace
    #
    # trace_result['result'] = onsway_trace(trace_condition)
    #
    # if trace_condition.reverse:
    #     reverse_condition = Conditions()
    #     reverse_condition.src_ip = trace_condition.dest_ip
    #     reverse_condition.dest_ip = trace_condition.src_ip
    #
    #     # TODO down direction trace
    #
    # trace_result.update({'trace_result': 'Success'})
    # return trace_result


def check_condition(cond_json):
    condition_obj = Conditions()

    condition_obj.src_ip = cond_json['source_ip']
    condition_obj.dest_ip = cond_json['destination_ip']

    if 'reverse' not in dict(cond_json).keys():
        condition_obj.reverse = False
    else:
        condition_obj.reverse = cond_json['reverse']

    return condition_obj


def get_topology(trace_condition):
    topology_obj = Topology()

    return topology_obj


def onsway_trace(trace_conditions):
    # TODO: ip check(format, subnet)
    # TODO: 1st location, inport
    # TODO: trace continue
    trace_result = {}

    return trace_result
