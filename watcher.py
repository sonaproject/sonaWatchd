#!/usr/bin/python
d# Copyright (c) 2017 by Telcoware
# SONA Monitoring Solutions.
# All Rights Reserved.


from daemon import Daemon
import sys
import time
import logging

PIDFILE = '/tmp/yourdaemon.pid'
LOGFILE = '/tmp/yourdaemon.log'

# Configure logging; delelete soon
logging.basicConfig(filename=LOGFILE,level=logging.DEBUG)


class SonaWatchD(Daemon):

    def run(self):
        # Loggigng errors and exceptions
        try:
            pass
        except Exception, e:
            logging.exception('Human friendly error message, '
                              'the exception will be captured '
                              'and added to the log file automaticaly')

        while True:
            # TODO
            # how to run http daemon?
            # implement periodic system check method
            logging.info('kjt ---- aaaa')
            time.sleep(5)

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
