#!/usr/bin/python
# Copyright (c) 2017 by Telcoware
# SONA Monitoring Solutions.
# All Rights Reserved.


from daemon import Daemon
import sys
import os
import time
import logging
import multiprocessing as MultiProcess

import api.rest_server as RestServer

PIDFILE = '/tmp/sonawatcher.pid'
LOGFILE = '/tmp/sonawatcher.log'

# Configure logging; delelete soon
logging.basicConfig(filename=LOGFILE,level=logging.DEBUG)


class SonaWatchD(Daemon):
    rs_t = MultiProcess

    def run(self):
        try:
            # pass
            self.rest_server_start()
        except Exception, e:
            logging.exception("%s", e.message)

        while True:
            # TODO
            # how to run http daemon?
            # implement periodic system check method
            time.sleep(5)

    # REST server start
    def rest_server_start(self):
        self.rs_t = MultiProcess.Process(name='rest_server', target=RestServer.run)
        self.rs_t.daemon = True
        self.rs_t.start()

if __name__ == "__main__":
    # implement config read ?

    daemon = SonaWatchD(PIDFILE)

    if len(sys.argv) == 2:

        if 'start' == sys.argv[1]:
            try:
                daemon.start()
            except:
                pass

        elif 'stop' == sys.argv[1]:
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
