from api.sona_log import LOG
from api.config import CONF
from api.watcherdb import DB
from api.sbapi import SshCommand

def vrouter_check(conn, node_name, user_name, node_ip):
    str_docker = ''
    onos_id = ''

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
                    onos_id = tmp_line[0]

                    if not 'Up' in line:
                        ret_docker = 'nok'

            if not (quagga_count == 2 and onos_count == 1):
                ret_docker = 'nok'
        except:
            LOG.exception()
    else:
        LOG.error("\'%s\' Vrouter Node Check Error", node_ip)
        str_docker = 'fail'

    str_onosapp = 'fail'
    str_route = 'fail'

    if onos_count == 1:
        # get onos container ip
        onos_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo docker inspect ' + onos_id + ' | grep IPAddress')

        if onos_rt is not None:
            for line in onos_rt.splitlines():
                line = line.strip()
                if line.startswith('\"IPAddress'):
                    tmp = line.split(':')
                    onos_ip = tmp[1].strip().replace('\"', '').replace(',', '')
                    break

            str_onosapp = SshCommand.ssh_pexpect(user_name, node_ip, onos_ip, 'apps -a -s')
            str_route = SshCommand.ssh_pexpect(user_name, node_ip, onos_ip, 'routes')
        else:
            LOG.info('@@ onos_rt is none')

    try:
        sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
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


def get_gw_ratio(conn, node_name, cur_val, total_val):
    try:
        if cur_val == -1 or total_val == 0:
            LOG.info('GW Ratio Fail.')
            return 'fail'

        if cur_val == 0:
            ratio = 0
        else:
            ratio = float(cur_val) * 100 / total_val

        strRatio = str(ratio) + ' (' + str(cur_val) + '/' + str(total_val) + ')'

        try:
            sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
                  ' SET gw_ratio = \'' + strRatio + '\'' + \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update GW Ratio info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('DB Update Fail.')
        except:
            LOG.exception()

        LOG.info('GW Ratio = ' + str(ratio))
        if ratio < float(CONF.alarm()['gw_ratio']):
            return 'nok'

        return 'ok'
    except:
        LOG.exception()
        return 'fail'


def gw_check(user_name, node_ip):
    try:
        port_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo ovs-ofctl show br-int | grep vxlan')
        port = int(port_rt.split('(')[0].strip())

        port_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo ovs-ofctl dump-ports br-int')

        for line in port_rt.splitlines():
            if line.split(':')[0].replace(' ', '') == 'port' + str(port):
                packet_cnt = int(line.split(',')[0].split('=')[1])

                return packet_cnt
    except:
        LOG.exception()

    return -1



