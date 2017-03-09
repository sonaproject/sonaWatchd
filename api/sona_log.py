# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

# generate example messages
#     logger.debug('debug message')
#     logger.info('informational message')
#     logger.warn('warning')
#     logger.error('error message')
#     logger.critical('critical failure')
# example log line) 2017-03-08 15:20:43,802 __main__ CRITICAL critical failure


import sys
import os
import logging
import traceback
from logging.handlers import TimedRotatingFileHandler
from config import CONF


class Log:
    LOG = logging.getLogger(__name__)

    def __init__(self):
        log_path = os.getcwd() + "/log/"
        if not os.path.exists(log_path):
            os.makedirs(log_path)
        file_name = log_path + CONF.base()['log_file_name']

        # formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
        formatter = logging.Formatter('%(asctime)s %(message)s')
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
