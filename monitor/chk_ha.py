from subprocess import Popen, PIPE
import csv

from api.sona_log import LOG
from api.watcherdb import DB
from api.config import CONF


def onos_ha_check(conn):
    try:
        stats_url = CONF.ha()['ha_proxy_server']
        account = CONF.ha()['ha_proxy_account']

        cmd = 'curl --user ' + account + ' --header \'Accept: text/html, application/xhtml+xml, image/jxr, */*\' \"' + stats_url + '\"'
        result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, error = result.communicate()

        if result.returncode != 0:
            LOG.error("Cmd Fail, cause => %s", error)
        else:
            report_data = csv.DictReader(output.lstrip('# ').splitlines())

        dic_stat = dict()
        for row in report_data:
            if row['pxname'].strip() == 'stats' or row['svname'].strip() == 'BACKEND':
                continue

            dtl_list = {'name': row['svname'], 'req_count': row['stot'], 'succ_count': row['hrsp_2xx'], 'node_sts': row['status']}

            svc_type = row['pxname']

            if (dic_stat.has_key(svc_type)):
                dic_stat[svc_type].append(dtl_list)
            else:
                dic_stat[svc_type] = list()
                dic_stat[svc_type].append(dtl_list)

        try:
            str_dic_stat = str(dic_stat)

            sql = 'UPDATE ' + DB.HA_TBL + \
                  ' SET stats = \"' + str_dic_stat + '\"' + \
                  ' WHERE ha_key = \"' + 'HA' + '\"'
            LOG.info('Update HA info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('HA DB Update Fail.')
        except:
            LOG.exception()

        return dic_stat
    except:
        LOG.exception()
        return None


def get_ha_stats(conn, ha_dic):
    try:
        ha_status = 'ok'
        ha_ratio = 'ok'

        str_list = ''

        frontend = 0
        backend = 0

        for key in dict(ha_dic).keys():
            for line in ha_dic[key]:
                host = dict(line)['name']
                status = dict(line)['node_sts']

                if not 'UP' in status:
                    ha_status = 'nok'

                    str_list = str_list + key + ' : ' + status + '\n'

                if host == 'FRONTEND':
                    frontend = int(dict(line)['req_count'])
                else:
                    backend = backend + int(dict(line)['succ_count'])

        ratio = float(backend) * 100 / frontend

        if ratio < float(CONF.alarm()['ha_proxy']):
            ha_ratio = 'nok'

        try:
            sql = 'UPDATE ' + DB.HA_TBL + \
                  ' SET haproxy = \'' + str_list + '\'' + \
                  ' WHERE ha_key = \"' + 'HA' + '\"'
            LOG.info('Update HA info = ' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                LOG.error('ONOS(HA STAT) DB Update Fail.')
        except:
            LOG.exception()

        return ha_status, ha_ratio
    except:
        LOG.exception()
        return 'fail', 'fail'

