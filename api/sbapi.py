# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import pexpect
import os

from subprocess import Popen, PIPE
from config import CONF
from sona_log import LOG

class SshCommand:
    ssh_options = '-o StrictHostKeyChecking=no ' \
              '-o ConnectTimeout=' + str(CONF.ssh_conn()['ssh_req_timeout'])

    @classmethod
    def ssh_exec(cls, username, node_ip, command):
        cmd = 'ssh %s %s@%s %s' % (cls.ssh_options, username, node_ip, command)
        LOG.info("SB SSH CMD] cmd = %s", cmd)

        try:
            result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
            output, error = result.communicate()

            if result.returncode != 0:
                LOG.error("\'%s\' SSH_Cmd Fail, cause => %s", node_ip, error)
                return
            else:
                # LOG.info("ssh command execute successful \n%s", output)
                return output
        except:
            LOG.exception()

    @classmethod
    def ssh_tperf_exec(cls, keypair, username, node_ip, command, timeout):
        ssh_options = '-o StrictHostKeyChecking=no ' \
                      '-o ConnectTimeout=' + str(timeout)

        if not os.path.exists(keypair):
            LOG.error('[SSH Fail] keypaire file not exist. ---')
            return 'fail'
        cmd = 'ssh %s -i %s %s@%s %s' % (ssh_options, keypair, username, node_ip, command)
        LOG.info("[SB SSH CMD] cmd = %s", cmd)

        try:
            result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
            (output, error) = result.communicate()

            if result.returncode != 0:
                LOG.error("\'%s\' SSH_Cmd Fail, cause(%d) => %s", node_ip, result.returncode, str(error))
                return 'fail'
            else:
                LOG.info("ssh command execute successful \n >> [%s]", output)
                return output
        except:
            LOG.exception()

        pass

    @classmethod
    def onos_ssh_exec(cls, node_ip, command):
        local_ssh_options = cls.ssh_options + " -p 8101"

        cmd = 'ssh %s %s %s' % (local_ssh_options, node_ip, command)
        LOG.info("SB SSH CMD] cmd = %s", cmd)

        try:
            result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
            output, error = result.communicate()

            if result.returncode != 0:
                LOG.error("ONOS(%s) SSH_Cmd Fail, cause => %s", node_ip, error)
                return
            else:
                # LOG.info("ONOS ssh command execute successful \n%s", output)
                return output
        except:
            LOG.exception()

    @classmethod
    def ssh_pexpect(cls, username, node_ip, onos_ip, command):
        cmd = 'ssh %s %s@%s' % (cls.ssh_options, username, node_ip)
        LOG.info("SB SSH CMD] cmd = %s", cmd)

        try:
            LOG.info('ssh_pexpect cmd = ' + cmd)
            ssh_conn = pexpect.spawn(cmd)

            rt1 = ssh_conn.expect(['#', '\$', pexpect.EOF], timeout=CONF.ssh_conn()['ssh_req_timeout'])

            if rt1 == 0:
                cmd = 'ssh -p 8101 karaf@' + onos_ip + ' ' + command

                LOG.info('ssh_pexpect cmd = ' + cmd)
                ssh_conn.sendline(cmd)
                rt2 = ssh_conn.expect(['Password:', pexpect.EOF], timeout=CONF.ssh_conn()['ssh_req_timeout'])

                if rt2 == 0:
                    ssh_conn.sendline('karaf')
                    ssh_conn.expect(['#', '\$', pexpect.EOF], timeout=CONF.ssh_conn()['ssh_req_timeout'])

                    str_output = str(ssh_conn.before)

                    ret = ''
                    for line in str_output.splitlines():
                        if (line.strip() == '') or ('#' in line) or ('$' in line) or ('~' in line) or ('@' in line):
                            continue

                        ret = ret + line + '\n'

                    return ret
                else:
                    return "fail"
            elif rt1 == 1:
                LOG.error('%s', ssh_conn.before)
            elif rt1 == 2:
                LOG.error("[ssh_pexpect] connection timeout")

            return "fail"
        except:
            LOG.exception()
            return "fail"

