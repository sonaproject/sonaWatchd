#!/usr/bin/python
# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.


import sys
import time
import multiprocessing as multiprocess

import api.rest_server as rest_svr
import api.watchdog as watchdog

from daemon import Daemon
from api.config import ConfReader

PIDFILE = ConfReader().pid_file()


class SonaWatchD(Daemon):

    def run(self):
        try:
            # TODO
            # develop REST API SERVER
            # self.rest_server_start()
            pass

        except Exception, e:
            sys.stderr.write("%s" % e)
            exit(1)

        while True:
            # TODO
            # how to run http daemon?
            # implement periodic system check method
            watchdog.temp()
            time.sleep(5)

    # REST server start
    def rest_server_start(self):
        rs_t = multiprocess.Process(name='rest_server', target=rest_svr.run)
        rs_t.daemon = True
        rs_t.start()

if __name__ == "__main__":
    # implement config file path read ?

    daemon = SonaWatchD(PIDFILE)

    if len(sys.argv) == 2:

        if 'start' == sys.argv[1]:
            try:
                daemon.start()
            except:
                pass

        elif 'stop' == sys.argv[1]:
            # print MyConf.obj.ConfMap['KJT_pidfile']
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
