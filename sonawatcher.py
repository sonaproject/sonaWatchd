#!/usr/bin/python
# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.


import multiprocessing as multiprocess
import sys
import time

import api.rest_server as rest_svr
import monitor.watchdog as watchdog
from api.config import CONF
from api.sona_log import LOG
from daemon import Daemon

# INTERVAL = CONF.watchdog()['system_check_interval']
PIDFILE = CONF.get_pid_file()


class SonaWatchD(Daemon):

    def run(self):
        try:
            # TODO
            # develop REST API SERVER
            LOG.info("--- REST Server START ---")
            # rest_svr.rest_server_start()
            pass
        except Exception, e:
            LOG.exception()
            exit(1)

        while True:
            # TODO
            # implement periodic system check method
            watchdog.temp()
            time.sleep(CONF.watchdog()['system_check_interval'])

if __name__ == "__main__":
    # implement config file path read ?

    daemon = SonaWatchD(PIDFILE)

    if len(sys.argv) == 2:

        if 'start' == sys.argv[1]:
            try:
                LOG.info("--- Daemon START ---")
                daemon.start()
            except:
                pass

        elif 'stop' == sys.argv[1]:
            LOG.info("--- Daemon STOP ---")
            print "Stopping ..."
            daemon.stop()

        elif 'restart' == sys.argv[1]:
            print "Restaring ..."
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
