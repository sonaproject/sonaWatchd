#!/usr/bin/python
# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import ConfigParser
import imp
import subprocess
import os

CONFIG_FILE = 'setup_config.ini'
REQUIREMENT_PKG = 'pexpect'
SSH_TIMEOUT = 3
ID_RAS_FILE = os.getenv('HOME') + '/.ssh/id_rsa.pub'

ONOS_INSTALL_DIR = '/opt/onos'


def installed_package(package):
    try:
        imp.find_module(package)
        return True
    except ImportError:
        return False


def install_package(package):
    try:
        import pip
        return pip.main(['install', package])
    except ImportError:
        print "Must install \"%s\" Package" % package
        exit(1)

if installed_package(REQUIREMENT_PKG):
    import pexpect
else:
    if install_package(REQUIREMENT_PKG) == 0:
        import pexpect
    else:
        print "Must install \"%s\" Package" % REQUIREMENT_PKG
        exit(1)


class CONF:
    def __init__(self):
        self.conf = ConfigParser.ConfigParser()
        self.conf.read(CONFIG_FILE)

    def get(self, session=None):
        conf_map = dict()
        for section in self.conf.sections():
            conf_map[section] = {key: value for key, value in self.conf.items(section)}

        if session is None:
            return conf_map
        else:
            return conf_map[session]


def ssh_keygen():
    print "[Setup] No ssh id_rsa and id_rsa.pub file ......"
    print "[Setup] Make ssh id_rsa and id_rsa.pub file ......"

    subprocess.call('ssh-keygen -t rsa -f ~/.ssh/id_rsa -P \'\' -q', shell=True)


def key_copy(node, conf):
    cmd = 'ssh-copy-id -oStrictHostKeyChecking=no -i %s/.ssh/id_rsa.pub %s@%s' \
          % (os.getenv('HOME'), conf['username'], node)
    ssh_conn = pexpect.spawn(cmd)

    while True:
        rt = ssh_conn.expect(['password:', pexpect.EOF], timeout=SSH_TIMEOUT)
        if rt == 0:
            if str(conf['auto_password']).lower() in ['No', 'no', 'NO']:
                password = str(raw_input("\n[Setup] Input %s password: " % node))
            else:
                password = conf['password']

            ssh_conn.sendline(password)

        elif rt == 1:
            ssh_print(node, ssh_conn.before.splitlines())
            break
        elif rt == 2:
            print "[Error] I either got key or connection timeout"


def key_copy_2onos(node, conf):
    print "[Setup] ONOS(%s) Prune the node entry from the known hosts file ......" % node
    prune_ssh_key_cmd = 'ssh-keygen -f "%s/.ssh/known_hosts" -R %s:8101' % (os.getenv('HOME'), node)
    subprocess.call(prune_ssh_key_cmd, shell=True)

    print "[Setup] ONOS(%s) Setup passwordless login for the local user ......" % node

    id_pub_file = file(ID_RAS_FILE, 'r')
    ssh_key = id_pub_file.read().split(" ")[1]
    id_pub_file.close()
    if ssh_key == '':
        print "[Setup] Read id_ras.pub file Fail ......"
        exit(1)

    set_ssh_key_cmd = 'ssh %s@%s %s/bin/onos-user-key %s %s' % \
                      (conf['username'], node, ONOS_INSTALL_DIR, os.getenv('USER'), ssh_key)
    subprocess.call(set_ssh_key_cmd, shell=True)


def ssh_print(node, lines):
    for line in lines:
        if line != '':
            print "[Setup] %s; %s" % (node, line)


def onos():
    print "\n\n[Setup] Start to copy ssh-key to ONOS systems ......"

    conf = CONF().get('ONOS')
    for node in str(conf['list']).replace(" ", "").split(","):
        key_copy(node, conf)
        key_copy_2onos(node, conf)


def xos():
    print "\n\n[Setup] Start to copy ssh-key to XOS systems ......"


def k8s():
    print "\n\n[Setup] Start to copy ssh-key to K8S systems ......"


def openstack():
    print "\n\n[Setup] Start to copy ssh-key to OpenStack systems ......"

    conf = CONF().get('OPENSTACK')
    for node in str(conf['list']).replace(" ", "").split(","):
        key_copy(node, conf)


def main():
    print "[Setup] ssh-key copy to start ......"

    print "[Setup] checking ssh id_pub key ......"
    if "id_rsa" not in os.listdir(os.getenv('HOME') + '/.ssh'):
        ssh_keygen()
    else:
        print "[Setup] ssh id_pub key exist ......"

    for node in str(CONF().get('BASE')['key_share_node']).replace(" ", "").split(","):
        if node.__eq__('ONOS'):
            onos()
        if node.__eq__('XOS'):
            xos()
        if node.__eq__('K8S'):
            k8s()
        if node.__eq__('OPENSTACK'):
            openstack()


if __name__ == "__main__":
    main()
    pass


