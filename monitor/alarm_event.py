import requests
import json

from datetime import datetime
from api.sona_log import LOG
from api.watcherdb import DB
from api.config import CONF

def is_monitor_item(node_type, item_type):
    conf_dict = CONF_MAP[node_type.upper()]()

    if conf_dict.has_key('alarm_off_list'):
        for item in (CONF_MAP[node_type.upper()]())['alarm_off_list']:
            if item_type in item:
                return False

    return True


def get_grade(item, value):
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


def occur_event(conn, node_name, item, pre_value, cur_value):
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

history_log = None
def set_history_log(log):
    global history_log
    history_log = log

def push_event(node_name, item, grade, desc, time):
    global history_log
    history_log.write_log('[%s][%s][%s] %s', node_name, item, grade, desc)

    sql = 'SELECT * FROM ' + DB.REGI_SYS_TBL

    with DB.connection() as conn:
        url_list = conn.cursor().execute(sql).fetchall()

    conn.close()

    for url, auth in url_list:
        header = {'Content-Type': 'application/json', 'Authorization': auth}
        req_body = {'event': 'occur', 'system': node_name, 'item': item, 'grade': grade, 'desc': desc, 'time': time}
        req_body_json = json.dumps(req_body)

        try:
            requests.post(url, headers=header, data=req_body_json, timeout = 2)
        except:
            # Push event does not respond
            pass


CONF_MAP = {'ONOS': CONF.onos,
            'XOS': CONF.xos,
            'SWARM': CONF.swarm,
            'OPENSTACK': CONF.openstack}