import cmd_proc
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


def get_gw_ratio(conn, node_name, node_ip, cur_val, total_val):
    try:
        sql = 'SELECT ' + DB.ONOS_TBL + '.nodename, nodelist, ip_addr' + ' FROM ' + DB.ONOS_TBL + \
                ' INNER JOIN ' + DB.NODE_INFO_TBL + ' ON ' + DB.ONOS_TBL + '.nodename = ' + DB.NODE_INFO_TBL + '.nodename'

        nodes_info = conn.cursor().execute(sql).fetchall()

        if len(nodes_info) == 0:
            LOG.info('Fail to load onos list')
            return 'fail'

        # search data_ip
        data_ip = ''
        manage_ip = ''
        packet_cnt = 0
        for nodename, nodelist, ip in nodes_info:
            if not nodelist == 'none':
                for line in str(nodelist).splitlines():
                    if 'managementIp=' + node_ip + ',' in line:
                        tmp = line.split(',')

                        for col in tmp:
                            if 'managementIp' in col:
                                data_ip = col.split('=')[1]
                                manage_ip = ip
                                break

                    if not manage_ip == '':
                        break
            if not manage_ip == '':
                break

        if data_ip == '':
            LOG.info('Can not find data ip')
            return 'fail'

        group_rt = SshCommand.onos_ssh_exec(manage_ip, 'groups')

        if group_rt is not None:
            for line in group_rt.splitlines():
                if '{tunnelDst=' + data_ip + '}' in line:
                    tmp = line.split(',')

                    for col in tmp:
                        if 'packets=' in col:
                            packet_cnt = packet_cnt + int(col.split('=')[1])

        if cur_val == -1 or total_val == 0:
            LOG.info('GW Ratio Fail.')
            strRatio = 'fail'
            ratio = 0
        else:
            if cur_val == 0:
                ratio = 0
            else:
                ratio = float(cur_val) * 100 / total_val

            strRatio = 'Received packet count = ' + str(cur_val) + '\n'
            strRatio = strRatio + 'compute nodes -> ' + node_name + ' Packet count = ' + str(packet_cnt) + '\n'
            strRatio = strRatio + str(ratio) + ' (' + str(cur_val) + ' / ' + str(total_val) + ')'

            if cur_val < packet_cnt:
                LOG.info('GW Ratio Fail. (Data loss)')
                strRatio = strRatio + '(packet loss)'
            else:
                strRatio = strRatio + '(no packet loss)'

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
        if ratio < float(CONF.alarm()['gw_ratio']) or cur_val < packet_cnt:
            return 'nok'

        return 'ok'
    except:
        LOG.exception()
        return 'fail'


def rx_tx_check(user_name, node_ip):
    try:
        port_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo ovs-ofctl show br-int | grep vxlan')

        if port_rt is not None:
            port = int(str(port_rt).split('(')[0].strip())

            port_rt = SshCommand.ssh_exec(user_name, node_ip, 'sudo ovs-ofctl dump-ports br-int')

            if port_rt is not None:
                i = 0
                for line in port_rt.splitlines():
                    i = i + 1
                    if line.split(':')[0].replace(' ', '') == 'port' + str(port):
                        rx_packet_cnt = int(line.split(',')[0].split('=')[1])
                        break

                tx_packet_cnt = int(port_rt.splitlines()[i].split(',')[0].split('=')[1])

                return rx_packet_cnt, tx_packet_cnt
    except:
        LOG.exception()

    return -1, -1


def calc_node_traffic_ratio(total_rx, total_tx):
    try:
        if total_tx == 0:
            LOG.info('Node Traffic Ratio Fail.')
            ratio = 0
        else:
            if total_rx == 0:
                ratio = 0
            else:
                ratio = float(total_rx) * 100 / total_tx


        LOG.info('Node Traffic Ratio = ' + str(ratio))
        return ratio
    except:
        LOG.exception()
        return -1


def get_node_traffic(conn, node_name, ratio, rx_dic, tx_dic, rx_total, tx_total):
    try:
        strRatio = '(VXLAN) Received packet count = ' + str(rx_dic[node_name]) + '\n'
        strRatio = strRatio + '(VXLAN) Sent packet count = ' + str(tx_dic[node_name]) + '\n'
        strRatio = strRatio + 'Ratio of success for all nodes = ' + str(ratio)  + ' (' + str(rx_total) + ' / ' + str(tx_total) + ')'

        try:
            sql = 'UPDATE ' + DB.OPENSTACK_TBL + \
                  ' SET vxlan_traffic = \'' + strRatio + '\'' + \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update Node Traffic Ratio info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('DB Update Fail.')
        except:
            LOG.exception()

        LOG.info('GW Ratio = ' + str(ratio))
        if ratio < float(CONF.alarm()['node_traffic_ratio']):
            return 'nok'

        return 'ok'
    except:
        LOG.exception()
        return 'fail'




