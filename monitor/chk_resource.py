# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

from api.sona_log import LOG
from api.sbapi import SshCommand
from api.watcherdb import DB

def get_cpu_usage(username, node_ip, only_value = False):
    try:
        cmd = 'sudo grep \'cpu\ \' /proc/stat'
        cmd_rt = SshCommand.ssh_exec(username, node_ip, cmd)

        ratio = float()
        if cmd_rt is None:
            LOG.info("%s CPU check Fail", node_ip)

            if only_value:
                return -1

            return {'CPU': 'Command fail'}
        else:
            if 'cpu ' in cmd_rt:
                try:
                    f = cmd_rt.split()
                    ratio = (float(f[1]) + float(f[3])) * 100 / \
                            (float(f[1]) + float(f[3]) + float(f[4]))
                except:
                    LOG.exception()

        result = {'CPU': {'RATIO': float(format(ratio, '.2f')), 'Description': cmd_rt}}
        LOG.info("CPU : %s", str(format(ratio, '.2f')))

        if only_value:
            return float(format(ratio, '.2f'))

        return result
    except:
        LOG.exception()
        return -1


def get_mem_usage(username, node_ip, only_value = False):
    try:
        cmd = 'sudo free -t -m | grep Mem'
        cmd_rt = SshCommand.ssh_exec(username, node_ip, cmd)

        ratio = float()
        if cmd_rt is None:
            LOG.info("%s Memory check Fail", node_ip)

            if only_value:
                return -1

            return {'MEMORY': 'Command fail'}
        else:
            if 'Mem' in cmd_rt:
                try:
                    f = cmd_rt.split()
                    ratio = float(f[2]) * 100 / float(f[1])
                except:
                    LOG.exception()

        result = {'MEMORY': {'RATIO': float(format(ratio, '.2f')), 'Description': cmd_rt}}
        LOG.info("MEMORY : %s", str(format(ratio, '.2f')))

        if only_value:
            return float(format(ratio, '.2f'))

        return result
    except:
        LOG.exception()
        return -1


def get_disk_usage(username, node_ip, only_value = False):
    try:
        cmd = 'sudo df -h / | grep -v Filesystem'
        cmd_rt = SshCommand.ssh_exec(username, node_ip, cmd)

        ratio = float()
        if cmd_rt is None:
            LOG.info("%s Diksk check Fail", node_ip)

            if only_value:
                return -1

            return {'DISK': 'Command fail'}
        else:
            if '/' in cmd_rt:
                try:
                    ratio = float(cmd_rt.split()[-2].replace('%', ''))
                except:
                    LOG.exception()

        result = {'DISK': {'RATIO': float(format(ratio, '.2f')), 'Description': cmd_rt}}
        LOG.info("DISK : %s", str(format(ratio, '.2f')))

        if only_value:
            return float(format(ratio, '.2f'))

        return result
    except:
        LOG.exception()
        return -1


def check_resource(conn, db_log, node_name, user_name, node_ip):
    try:
        cpu = str(get_cpu_usage(user_name, node_ip, True))
        mem = str(get_mem_usage(user_name, node_ip, True))
        disk = str(get_disk_usage(user_name, node_ip, True))

        try:
            sql = 'UPDATE ' + DB.RESOURCE_TBL + \
                  ' SET cpu = \'' + cpu + '\',' + \
                  ' memory = \'' + mem + '\',' + \
                  ' disk = \'' + disk + '\'' \
                  ' WHERE nodename = \'' + node_name + '\''
            db_log.write_log('----- UPDATE RESOURCE INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] RESOURCE DB Update Fail.')
        except:
            LOG.exception()

        return cpu, mem, disk
    except:
        LOG.exception()
        return -1, -1, -1


PARAM_MAP = {'cpu': get_cpu_usage,
             'memory': get_mem_usage,
             'disk': get_disk_usage}
