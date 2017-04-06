import time

from system_info import SYS
from log_lib import LOG

WHITE = '\033[1;97m'
BLUE = '\033[1;94m'
YELLOW = '\033[1;93m'
GREEN = '\033[1;92m'
RED = '\033[1;91m'
BLACK = '\033[1;90m'
BG_WHITE = '\033[0;97m'
BG_BLUEW = '\033[0;37;44m'
BG_SKYW = '\033[0;37;46m'
BG_PINKW = '\033[0;37;45m'
BG_YELLOWW = '\033[0;30;43m'
BG_GREENW = '\033[0;37;42m'
BG_RED = '\033[0;91m'
BG_BLACK = '\033[0;90m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'

MAIN_WIDTH = 50

class SCREEN():
    @classmethod
    def draw_system(cls):
        try:
            now = time.localtime()
            str_time = 'Last Check Time [%02d:%02d:%02d]' % (now.tm_hour, now.tm_min, now.tm_sec)
            #cls.set_main_str(SYS.get_onos_line_count() + 2 + 4 + 1, MAIN_WIDTH - len(str_time), str_time, time_color)
        except:
            LOG.exception_err_write()

    @classmethod
    def display_header(cls, menu):
        try:
            width = 60
            print BG_WHITE + "|%s|" % ('-' * width).ljust(width) + ENDC
            print BG_WHITE + '|' + BG_BLUEW + BOLD + \
                    ("{0:^" + str(width) + "}").format(menu) + BG_WHITE + '|' + ENDC
            print BG_WHITE + "|%s|" % ('-' * width).ljust(width) + ENDC
        except:
            LOG.exception_err_write()
