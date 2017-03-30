# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

from subprocess import Popen, PIPE

from config import CONF
from sona_log import LOG


class SshCommand:
    ssh_opt = '-o StrictHostKeyChecking=no ' \
              '-o ConnectTimeout=' + str(CONF.ssh_conn()['ssh_req_timeout'])

    @classmethod
    def execute(cls, username, node, command):
        cmd = 'ssh %s %s@%s %s' % (cls.ssh_opt, username, node, command)
        LOG.error('Command: %s', cmd)

        result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, error = result.communicate()

        if result.returncode != 0:
            LOG.error("Execution Error(%d): %s", result.returncode, error)
            return
        else:
            return output


class RestGet:
    pass
