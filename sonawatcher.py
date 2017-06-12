#!/usr/bin/python
# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.


import sys
import time

import monitor.alarm_event as alarm_event
import monitor.watchdog as watchdog
import api.rest_server as REST_SVR
from api.config import CONF
from api.sona_log import LOG
from api.sona_log import USER_LOG
from api.watcherdb import DB
from daemon import Daemon
from datetime import datetime

PIDFILE = CONF.get_pid_file()


class SonaWatchD(Daemon):
    def run(self):

        # DB initiation
        DB.db_initiation()

        # Start RESTful server
        try:
            REST_SVR.rest_server_start()
        except:
            print 'Rest Server failed to start'
            LOG.exception()
            sys.exit(1)

        # Periodic monitoring
        if CONF.watchdog()['interval'] == 0:
            LOG.info("--- Not running periodic monitoring ---")
            while True:
                time.sleep(3600)
        else:
            LOG.info("--- Periodic Monitoring Start ---")
            history_log.write_log("--- Event History Start ---")

            conn = DB.connection()

            while True:
                try:
                    watchdog.periodic(conn, history_log)

                    time.sleep(CONF.watchdog()['interval'])
                except:
                    alarm_event.push_event('sonawatcher', 'SONAWATCHER_DISCONNECT', 'critical', 'sonawatcher server shutdown', str(datetime.now()))
                    conn.close()
                    LOG.exception()
                    sys.exit(1)


if __name__ == "__main__":
    history_log = USER_LOG()
    history_log.set_log('event_history.log', CONF.base()['log_rotate_time'], CONF.base()['log_backup_count'])
    alarm_event.set_history_log(history_log)

    daemon = SonaWatchD(PIDFILE)

    if len(sys.argv) == 2:

        if 'start' == sys.argv[1]:
            try:
                daemon.start()
            except:
                pass

        elif 'stop' == sys.argv[1]:
            print "Stopping ..."
            try:
                alarm_event.push_event('sonawatcher', 'SONAWATCHER_DISCONNECT', 'critical', 'sonawatcher server shutdown', str(datetime.now()))
            except:
                pass
            daemon.stop()

        elif 'restart' == sys.argv[1]:
            print "Restaring ..."
            try:
                alarm_event.push_event('sonawatcher', 'SONAWATCHER_DISCONNECT', 'critical', 'sonawatcher server shutdown', str(datetime.now()))
            except:
                pass
            daemon.restart()

        elif 'status' == sys.argv[1]:
            try:
                pf = file(PIDFILE,'r')
                pid = int(pf.read().strip())
                pf.close()
            except IOError:
                pid = None
            except SystemExit:
                pid = None

            if pid:
                print 'YourDaemon is running as pid %s' % pid
            else:
                print 'YourDaemon is not running.'

        else:
            print "Unknown command"
            sys.exit(2)

    else:
        print "usage: %s start|stop|restart|status" % sys.argv[0]
        sys.exit(2)
