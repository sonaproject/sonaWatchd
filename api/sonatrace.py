# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

from sona_log import LOG
import re
from config import CONF
from sbapi import SshCommand

class Conditions:
    cond_dict = dict()
    def __init__(self):
        self.cond_dict["in_port"] = ''
        self.cond_dict["dl_src"] = ''
        self.cond_dict["dl_dst"] = ''
        self.cond_dict["dl_type"] = ''
        self.cond_dict["nw_src"] = ''
        self.cond_dict["nw_dst"] = ''
        self.cond_dict["nw_proto"] = ''
        self.cond_dict["tp_src"] = ''
        self.cond_dict["tp_dst"] = ''
        self.cond_dict["tun_id"] = ''

        self.reverse = False
        self.cur_target_ip = ''
        self.cur_target_hostname = ''


class Topology:
    ONOS_SUBNET = 'openstack-networks'
    ONOS_HOST = 'hosts'
    ONOS_DEVICE = 'devices'
    ONOS_FLOATINGIP = 'openstack-floatingips'
    ONOS_OPENSTACKNODES = 'openstack-nodes'

    def __init__(self):
        self.subnets = self.get_subnets(self.get_onos_ip())
        self.floatingips = self.get_floatingips(self.get_onos_ip())
        self.devices = []

    def get_hosts(self, onos_ip, find_cond):
        onos_ssh_result = SshCommand.onos_ssh_exec(onos_ip, self.ONOS_HOST + '| grep ' + find_cond)
        return onos_ssh_result

    def get_openstacknodes(self, onos_ip, find_cond):
        onos_ssh_result = SshCommand.onos_ssh_exec(onos_ip, self.ONOS_OPENSTACKNODES + '| grep ' + find_cond)
        return onos_ssh_result

    def get_onos_ip(self):
        return str(list(CONF.onos()['list']).pop()).split(':')[-1]

    def get_subnets(self, onos_ip):
        onos_ssh_result = SshCommand.onos_ssh_exec(onos_ip, self.ONOS_SUBNET)
        subnets = re.findall(r'[0-9]+(?:\.[0-9]+){3}(?:/\d\d)', onos_ssh_result)
        return subnets

    def get_floatingips(self, onos_ip):
        onos_ssh_result = SshCommand.onos_ssh_exec(onos_ip, self.ONOS_FLOATINGIP)
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

    # # TODO up direction trace
    #

    find_target(trace_condition, sona_topology)

    trace_result['up_result'] = onsway_trace(trace_condition)
    #
    # if trace_condition.reverse:
    #     reverse_condition = Conditions()
    #     reverse_condition.src_ip = trace_condition.dest_ip
    #     reverse_condition.dest_ip = trace_condition.src_ip
    #
    #     # TODO down direction trace
    #
    # trace_result.update({'trace_result': 'Success'})
    return trace_result


def find_target(trace_condition, sona_topology):
    # find switch info
    LOG.info('source ip = ' + trace_condition.cond_dict['nw_src'])
    result = sona_topology.get_hosts(sona_topology.get_onos_ip(), '\"\[' + trace_condition.cond_dict['nw_src'] + '\]\"')

    switch_info = (result.split(',')[2].split('=')[1])[1:-1]
    switch_id = switch_info.split('/')[0]
    vm_port = switch_info.split('/')[1]

    LOG.info('swtich id = ' + switch_id)

    # find target node
    node_info = sona_topology.get_openstacknodes(sona_topology.get_onos_ip(), switch_id)
    node_info = " ".join(node_info.split())

    tmp = node_info.split(' ')
    if tmp[3].startswith('of:'):
        target_ip = tmp[4]
    else:
        target_ip = tmp[3]

    LOG.info('target ip = ' + target_ip)

    trace_condition.cond_dict['in_port'] = vm_port
    trace_condition.cur_target_ip = target_ip
    trace_condition.cur_target_hostname = tmp[0]


def check_condition(cond_json):
    condition_obj = Conditions()

    for key in dict(cond_json).keys():
        if key == 'reverse':
            condition_obj.reverse = cond_json['reverse']
        elif key == 'source_ip':
            condition_obj.cond_dict['nw_src'] = cond_json['source_ip']
        elif key == 'destination_ip':
            condition_obj.cond_dict['nw_dst'] = cond_json['destination_ip']

    # check dl_dst/dl_type
    condition_obj.cond_dict['dl_dst'] = 'fe:00:00:00:00:02'
    condition_obj.cond_dict['dl_type'] = '0x0800'

    return condition_obj


def make_command(trace_conditions):
    cond_list = ''
    for key in dict(trace_conditions.cond_dict).keys():
        value = trace_conditions.cond_dict[key]

        if value != '':
            cond_list = cond_list + key + '=' + str(value) + ','

    command = 'ovs-appctl ofproto/trace br-int \'' + cond_list + '\''
    LOG.info('command = ' + command)

    return command


def onsway_trace(trace_conditions):
    # TODO: ip check(format, subnet)
    # TODO: 1st location, inport
    # TODO: trace continue

    retry_flag = True
    up_down_result = []

    while retry_flag:
        ssh_result = SshCommand.ssh_exec(CONF.openstack()['account'].split(':')[0], trace_conditions.cur_target_ip, make_command(trace_conditions))

        LOG.info('target_node = ' + trace_conditions.cur_target_ip)
        LOG.info('TRACE RESULT = ' + str(ssh_result))

        process_result, retry_flag = process_trace(ssh_result, trace_conditions)

        node_trace = dict()
        node_trace['trace_node_name'] = trace_conditions.cur_target_hostname
        node_trace['flow_rules'] = process_result
        up_down_result.append(node_trace)

    return up_down_result


def process_trace(output, trace_conditions):
    try:
        retry_flag = False

        result_flow = []
        lines = output.splitlines()

        for line in lines:
            line = line.strip()

            if line.startswith('Rule:'):
                rule_dict = dict()
                tmp = line.split(' ')
                rule_dict['table'] = int(tmp[1].split('=')[1])
                rule_dict['cookie'] = tmp[2].split('=')[1]

                for col in tmp[3].split(','):
                    tmp = col.split('=')

                    if len(tmp) == 2:
                        if tmp[0] in ['priority', 'in_port']:
                            rule_dict[tmp[0]] = int(tmp[1])
                        else:
                            rule_dict[tmp[0]] = tmp[1]

            elif line.startswith('OpenFlow actions='):
                action_dict = dict()
                setfield_dict = dict()

                action_list = line.split('=')[1].split(',')
                for action in action_list:
                    if action.startswith('set_field'):
                        type = action.split('->')[1]

                        setfield_dict[type] = action[action.find(':') + 1:action.find('-')]

                        if type == 'tun_dst':
                            #find next target
                            trace_conditions.cur_target_ip = '10.10.2.129'
                            trace_conditions.cur_target_hostname = 'compute-02'
                        else:
                            trace_conditions.cond_dict[type] = action[action.find(':') + 1:action.find('-')]
                    else:
                        action_dict['action'] = action

                if len(setfield_dict) > 0:
                    action_dict['set_field'] = setfield_dict

                flow_dict = dict()
                flow_dict['rule'] = rule_dict
                flow_dict['action'] = action_dict

                result_flow.append(flow_dict)

                if 'tun_dst' in line:
                    retry_flag = True

                if 'output' in line:
                    break

        return result_flow, retry_flag
    except:
        LOG.exception_err_write()
        return 'parsing error\n' + output
