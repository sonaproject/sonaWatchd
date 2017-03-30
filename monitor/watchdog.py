# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import sys

from subprocess import Popen
from subprocess import PIPE
from api.config import CONF
from api.sona_log import LOG
from api.sbapi import SshCommand


def periodic():
    LOG.info("Periodic checking...%s", str(CONF.watchdog()['check_system']))
    node_list = list()
    for node in CONF.watchdog()['check_system']:
        if str(node).lower() == 'onos':
            node_list += CONF.onos()['list']
        elif str(node).lower() == 'xos':
            node_list += CONF.xos()['list']
        elif str(node).lower() == 'k8s':
            node_list += CONF.k8s()['list']
        elif str(node).lower() == 'openstack':
            node_list += CONF.openstack_node()['list']

    # LOG.info("kjt --2-- %s", SshCommand.execute('root', '172.16.130.81', 'ls -al'))
    try:
        for node in node_list:
            node_name, node_ip = str(node).split(':')
            rt = net_check(node_ip)
            # TODO data caching
    except:
        LOG.exception()


def net_check(node):
    if CONF.watchdog()['method'] == 'ping':
        if sys.platform == 'darwin':
            timeout = CONF.watchdog()['timeout'] * 1000
        else:
            timeout = CONF.watchdog()['timeout']

        cmd = 'ping -c1 -W%d -n %s' % (timeout, node)
        # LOG.info("%s", cmd)

        result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, error = result.communicate()

        if result.returncode != 0:
            LOG.error("\'%s\' Network Check Error(errno: %d): %s", node, result.returncode, error)
            return 'fail'
        else:
            return 'alive'
