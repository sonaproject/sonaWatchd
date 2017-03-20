import os
import sys
import logging
import logging.handlers
import datetime
import traceback
from config import CONFIG

DEFAULT_LOG_PATH = os.getcwd() + "/log/"

class LOG():
    cli_log_flag = False
    trace_log_flag = False

    LOG = logging.getLogger(__name__)

    @classmethod
    def set_log(cls):
        if not os.path.exists(DEFAULT_LOG_PATH):
            os.makedirs(DEFAULT_LOG_PATH)

        log_formatter = logging.Formatter('[%(asctime)s] %(message)s')

        # set file name
        file_name = DEFAULT_LOG_PATH + 'sonawatched_cli.log'

        file_handler = logging.handlers.TimedRotatingFileHandler(file_name,
                                                                 when='D',
                                                                 backupCount=int(CONFIG.get_cli_log_backup()))

        file_handler.setFormatter(log_formatter)

        cls.LOG.addHandler(file_handler)
        cls.LOG.setLevel(logging.DEBUG)

    @classmethod
    def set_log_config(cls):
        if (CONFIG.get_cli_log().upper()) == 'ON':
            cls.cli_log_flag = True

        if (CONFIG.get_trace_log().upper()) == 'ON':
            cls.trace_log_flag = True

    @classmethod
    def cli_log(cls, log):
        try:
            if cls.cli_log_flag:
                cls.debug('[CLI] ' + log)
        except:
            cls.exception_err_write()

    @classmethod
    def trace_log(cls, log):
        try:
            if cls.trace_log_flag:
                cls.debug('[TRACE] ' + log)
        except:
            cls.exception_err_write()

    @classmethod
    def debug(cls, log):
        try:
            cls.LOG.debug(log)
        except:
            cls.exception_err_write()

    @classmethod
    def exception_err_write(cls):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        cls.LOG.debug("%s", ''.join('   || ' + line for line in lines))

