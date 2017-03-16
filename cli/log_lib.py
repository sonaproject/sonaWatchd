import sys
import logging
import logging.handlers
import datetime
import traceback
from config import CONFIG

class LOG():
    cli_log_flag = False
    trace_log_flag = False

    LOG = logging.getLogger(__name__)

    @classmethod
    def set_log(cls):
        log_formatter = logging.Formatter('[%(asctime)s] %(message)s')

        # set file name
        now = datetime.datetime.now()
        now_time = now.strftime('%Y-%m-%d')

        file_name = 'sona_watched_cli.' + now_time

        fileMaxByte = 1024 * 1024 * 100
        file_handler = logging.handlers.RotatingFileHandler(file_name, maxBytes=fileMaxByte, backupCount=10)
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

