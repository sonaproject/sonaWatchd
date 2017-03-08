import logging
import logging.handlers
import datetime

class LogLib():
    LOG = logging.getLogger(__name__)

    @classmethod
    def set_log(cls):
        log_formatter = logging.Formatter('[%(asctime)s] (%(levelname)7s) %(filename)s:%(lineno)s : %(message)s')

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
    def debug(cls, log):
        cls.LOG.debug(log)

