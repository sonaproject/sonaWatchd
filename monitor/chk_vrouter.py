from api.sona_log import LOG
from api.watcherdb import DB
from api.sbapi import SshCommand

def vrouter_check(conn, node_name, user_name, node_ip):
    str_docker = ''

    ret_docker = 'ok'

    docker_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo docker ps')

    if docker_rt is not None:
        quagga_count = 0
        onos_count = 0

        try:
            for line in docker_rt.splitlines():
                str_docker = str_docker + line + '\n'

                if line.startswith('CONTAINER'):
                    continue

                tmp_line = line.split()

                if 'quagga' in tmp_line[1]:
                    quagga_count = quagga_count + 1

                    if not 'Up' in line:
                        ret_docker = 'nok'

                elif 'onos' in tmp_line[1]:
                    onos_count = onos_count + 1

                    if not 'Up' in line:
                        ret_docker = 'nok'

            if not (quagga_count == 2 and onos_count == 1):
                ret_docker = 'nok'
        except:
            LOG.exception()
    else:
        LOG.error("\'%s\' Vrouter Node Check Error", node_ip)
        str_docker = 'fail'

    str_onosapp = SshCommand.ssh_pexpect(user_name, node_ip, 'apps -a -s')
    str_route = SshCommand.ssh_pexpect(user_name, node_ip, 'routes')

    try:
        sql = 'UPDATE ' + DB.VROUTER_TBL + \
              ' SET docker = \'' + str_docker + '\',' + \
              ' onosApp = \'' + str_onosapp + '\',' + \
              ' routingTable = \'' + str_route + '\'' + \
              ' WHERE nodename = \'' + node_name + '\''
        LOG.info('Update Vrouter info = ' + sql)

        if DB.sql_execute(sql, conn) != 'SUCCESS':
            LOG.error('DB Update Fail.')
    except:
        LOG.exception()

    return ret_docker