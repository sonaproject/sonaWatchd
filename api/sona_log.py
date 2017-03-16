# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

# Ref) generate example messages
#     logger.debug('debug message')
#     logger.info('informational message')
#     logger.warn('warning')
#     logger.error('error message')
#     logger.critical('critical failure')

import sys
import os
import logging
import traceback
from logging.handlers import TimedRotatingFileHandler
from config import CONF

DEFAULT_LOG_PATH = os.getcwd() + "/log/"
DEFAULT_LOGGER_NAME = 'sona_logger'


class Log:
    logger = logging.getLogger(DEFAULT_LOGGER_NAME)

    def __init__(self, file_name):
        if not os.path.exists(DEFAULT_LOG_PATH):
            os.makedirs(DEFAULT_LOG_PATH)
        log_file_name = DEFAULT_LOG_PATH + file_name

        # Ref) formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
        formatter = logging.Formatter('%(asctime)s.%(msecs)03d %(message)s',
                                      datefmt='(%m/%d) %H:%M:%S')
        handler = TimedRotatingFileHandler(log_file_name,
                                           when=CONF.base()['log_rotate_time'],
                                           backupCount=CONF.base()['log_backup_count'])
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    @classmethod
    def info(cls, message, *args):
        cls.logger.info(message % args)

    @classmethod
    def error(cls, message, *args):
        cls.logger.error(message % args)

    @classmethod
    def exception(cls):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        cls.error("%s", ''.join('   | ' + line for line in lines))


LOG = Log(CONF.base()['log_file_name'])

# TODO
# multiple create Logger point

