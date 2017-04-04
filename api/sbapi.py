# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

from subprocess import Popen, PIPE

from config import CONF
from sona_log import LOG


class SshCommand:
    ssh_options = '-o StrictHostKeyChecking=no ' \
              '-o ConnectTimeout=' + str(CONF.ssh_conn()['ssh_req_timeout'])

    @classmethod
    def ssh_exec(cls, username, node, command):
        cmd = 'ssh %s %s@%s %s' % (cls.ssh_options, username, node, command)
        # LOG.info('Command: %s', cmd)

        result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, error = result.communicate()

        if result.returncode != 0:
            LOG.error("Execution Error(%d): %s", result.returncode, error)
            return
        else:
            LOG.info("ssh command execute successful \n%s", output)
            return output

    @classmethod
    def onos_ssh_exec(cls, node, command):
        cls.ssh_options = cls.ssh_options + " -p 8101"

        cmd = 'ssh %s %s %s' % (cls.ssh_options, node, command)
        # LOG.info('Command: %s', cmd)

        result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, error = result.communicate()

        if result.returncode != 0:
            LOG.error("Execution Error(%d): %s", result.returncode, error)
            return
        else:
            # LOG.info("ONOS ssh command execute successful \n%s", output)
            return output
