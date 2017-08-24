from subprocess import Popen, PIPE
import time
import json

from api.sona_log import LOG
from api.watcherdb import DB
from api.config import CONF


def xos_status_check(conn, db_log, node_name):
    xos_status = 'ok'
    xos_list = []
    fail_reason = []

    try:
        url = CONF.xos()['xos_rest_server']
        account = CONF.xos()['xos_rest_account']

        cmd = 'curl -H "Accept: application/json; indent=4" -u ' + account + ' -X GET ' + url + '/api/core/xoses/'
        result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, error = result.communicate()

        if result.returncode != 0:
            LOG.error("Cmd Fail, cause => %s", error)
            return 'fail', None

        xos_array = json.loads(output)

        for xos_info in xos_array:
            backend_status = xos_info['backend_status']

            LOG.info('backend_status = ' + backend_status)

            tmp = str(backend_status).split('-')

            if tmp[0].strip() == '0':
                status = 'ok'
            else:
                status = 'nok'

            xos_json = {'name': xos_info['name'], 'status': status, 'description': tmp[1].strip()}
            xos_list.append(xos_json)

            if status == 'nok':
                xos_status = 'nok'
                fail_reason.append(xos_json)

            try:
                sql = 'UPDATE ' + DB.XOS_TBL + \
                      ' SET xos_status = \"' + str(xos_list) + '\"' + \
                      ' WHERE nodename = \'' + node_name + '\''
                db_log.write_log('----- UPDATE XOS STATUS INFO -----\n' + sql)

                if DB.sql_execute(sql, conn) != 'SUCCESS':
                    db_log.write_log('[FAIL] XOS STATUS DB Update Fail.')
            except:
                LOG.exception()

    except:
        LOG.exception()
        xos_status = 'fail'

    return xos_status, fail_reason


def xos_sync_check(conn, db_log, node_name):
    xos_sync = 'ok'
    sync_list = []
    fail_reason = []

    try:
        url = CONF.xos()['xos_rest_server']
        account = CONF.xos()['xos_rest_account']

        cmd = 'curl -H "Accept: application/json; indent=4" -u ' + account + ' -X GET ' + url + '/api/core/diags/'
        result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, error = result.communicate()

        if result.returncode != 0:
            LOG.error("Cmd Fail, cause => %s", error)
            return 'fail', None

        sync_array = json.loads(output)

        for xos_info in sync_array:
            backend_status = xos_info['backend_status']

            LOG.info('backend_status = ' + backend_status)

            tmp = str(backend_status).split('-')

            if tmp[0].strip() in ['0', '1']:
                status = 'ok'
            else:
                status = 'nok'

            # check time
            last_time = xos_info['backend_register']['last run']
            cur_time = time.time()

            interval = cur_time - last_time

            if interval >= 30:
                status = 'nok'

            xos_json = {'name': xos_info['name'], 'status': status, 'description': tmp[1].strip(), 'last_run_interval': interval}
            sync_list.append(xos_json)

            if status == 'nok':
                xos_sync = 'nok'
                fail_reason.append(xos_json)

            try:
                sql = 'UPDATE ' + DB.XOS_TBL + \
                      ' SET xos_status = \"' + str(sync_list) + '\"' + \
                      ' WHERE nodename = \'' + node_name + '\''
                db_log.write_log('----- UPDATE XOS STATUS INFO -----\n' + sql)

                if DB.sql_execute(sql, conn) != 'SUCCESS':
                    db_log.write_log('[FAIL] XOS STATUS DB Update Fail.')
            except:
                LOG.exception()

    except:
        LOG.exception()
        xos_sync = 'fail'

    return xos_sync, fail_reason


