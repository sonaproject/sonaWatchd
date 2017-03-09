# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import sys
import os
import logging
import traceback
from logging.handlers import TimedRotatingFileHandler
from config import CONF


LOG_PATH = os.getcwd() + "/log/"


class Log:
    LOG = logging.getLogger(__name__)

    def __init__(self):
        formatter = logging.Formatter('%(asctime)s %(message)s')
        file_name = LOG_PATH + CONF.base()['log_file_name']
        handler = TimedRotatingFileHandler(file_name,
                                           when=CONF.base()['log_rotate_time'],
                                           backupCount=CONF.base()['log_backup_count'])
        handler.setFormatter(formatter)
        self.LOG.addHandler(handler)
        self.LOG.setLevel(logging.DEBUG)

    @classmethod
    def info(cls, message, *args):
        cls.LOG.info(message % args)

    @classmethod
    def exception(cls):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        cls.info("%s", ''.join('   | ' + line for line in lines))


LOG = Log()

# generate example messages
# for i in range(10000):
#     time.sleep(10)
#     logger.debug('debug message')
#     logger.info('informational message')
#     logger.warn('warning')
#     logger.error('error message')
#     logger.critical('critical failure')


# 2017-03-08 15:20:43,802 __main__ CRITICAL critical failure