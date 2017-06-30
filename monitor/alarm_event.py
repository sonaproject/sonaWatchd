import requests
import json

from datetime import datetime
from api.sona_log import LOG
from api.watcherdb import DB
from api.config import CONF


def process_event(conn, node_name, type, id, pre_value, cur_value):
    try:
        if not is_monitor_item(type, id):
            return '-'
        elif pre_value != cur_value:
            occur_event(conn, node_name, id, pre_value, cur_value)

        return cur_value
    except:
        LOG.exception()


def is_monitor_item(node_type, item_type):
    try:
        conf_dict = CONF_MAP[node_type.upper()]()

        if conf_dict.has_key('alarm_off_list'):
            for item in (CONF_MAP[node_type.upper()]())['alarm_off_list']:
                if item_type in item:
                    return False
    except:
        LOG.exception()

    return True


def get_grade(item, value):
    try:
        critical, major, minor = (CONF.alarm()[item])

        if value == '-1':
            return 'fail'

        if float(value) >= float(critical):
            return 'critical'
        elif float(value) >= float(major):
            return 'major'
        elif float(value) >= float(minor):
            return 'minor'

        return 'normal'
    except:
        LOG.exception()
        return 'fail'


def occur_event(conn, node_name, item, pre_value, cur_value):
    try:
        time = str(datetime.now())
        desc = pre_value + ' -> ' + cur_value
        sql = 'UPDATE ' + DB.EVENT_TBL + \
              ' SET grade = \'' + cur_value + '\'' + ',' + \
              ' desc = \'' + desc + '\'' + ',' + \
              ' time = \'' + time + '\'' + \
              ' WHERE nodename = \'' + node_name + '\' and item = \'' + item + '\''
        LOG.info('Update alarm info = ' + sql)

        if DB.sql_execute(sql, conn) != 'SUCCESS':
            LOG.error('DB Update Fail.')

        push_event(node_name, item, cur_value, desc, time)
    except:
        LOG.exception()


history_log = None
def set_history_log(log):
    global history_log
    history_log = log


def push_event(node_name, item, grade, desc, time):
    global history_log

    try:
        history_log.write_log('[%s][%s][%s] %s', node_name, item, grade, desc)

        sql = 'SELECT * FROM ' + DB.REGI_SYS_TBL

        with DB.connection() as conn:
            url_list = conn.cursor().execute(sql).fetchall()

        conn.close()

        for url, auth in url_list:
            header = {'Content-Type': 'application/json', 'Authorization': auth}
            req_body = {'system': node_name, 'item': item, 'grade': grade, 'desc': desc, 'time': time}
            req_body_json = json.dumps(req_body)

            try:
                requests.post(url, headers=header, data=req_body_json, timeout = 2)
            except:
                # Push event does not respond
                pass
    except:
        LOG.exception()


CONF_MAP = {'ONOS': CONF.onos,
            'HA': CONF.ha,
            'XOS': CONF.xos,
            'SWARM': CONF.swarm,
            'OPENSTACK': CONF.openstack}