import curses
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
    main_scr = curses.initscr()

    @classmethod
    def set_screen(cls):
        curses.noecho()
        curses.cbreak()
        curses.start_color()
        cls.main_scr.keypad(1)
        curses.curs_set(0)
        cls.main_scr.refresh()

        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_MAGENTA, curses.COLOR_BLACK)

    @classmethod
    def set_main_str(cls, x, y, str, color):
        try:
            cls.main_scr.addstr(x, y, str, color)
            cls.refresh_screen()
        except:
            LOG.exception_err_write()

    @classmethod
    def screen_exit(cls):
        try:
            curses.endwin()
        except:
            LOG.exception_err_write()

    @classmethod
    def refresh_screen(cls):
        try:
            cls.main_scr.refresh()
        except:
            LOG.exception_err_write()

    @classmethod
    def get_screen(cls):
        return cls.main_scr

    @classmethod
    def get_ch(cls):
        try:
            return cls.main_scr.getch()
        except:
            LOG.exception_err_write()
            return ''

    @classmethod
    def draw_system(cls):
        try:
            box_onos = cls.display_onos_info(2)
            box_onos.refresh()

            time_color = curses.color_pair(3)

            now = time.localtime()
            str_time = 'Last Check Time [%02d:%02d:%02d]' % (now.tm_hour, now.tm_min, now.tm_sec)
            cls.set_main_str(SYS.get_onos_line_count() + 2 + 4 + 1, MAIN_WIDTH - len(str_time), str_time, time_color)
        except:
            LOG.exception_err_write()

    @classmethod
    def draw_menu(cls, menu_list, selected_menu_no):
        try:
            box_menu = cls.draw_select(menu_list, selected_menu_no)
            box_menu.refresh()
        except:
            LOG.exception_err_write()

    @staticmethod
    def draw_select(menu_list, selected_menu_no):
        box_type = curses.newwin(len(menu_list) + 2, MAIN_WIDTH, SYS.get_onos_line_count() + 3, 1)
        box_type.box()

        try:
            highlightText = curses.color_pair(1)
            normalText = curses.A_NORMAL

            box_type.addstr(0, 22, ' MENU ', normalText)

            for i in range(1, len(menu_list) + 1):
                if i is selected_menu_no:
                    box_type.addstr(i, 2, str(i) + "." + menu_list[i - 1], highlightText)
                else:
                    box_type.addstr(i, 2, str(i) + "." + menu_list[i - 1], normalText)
        except:
            LOG.exception_err_write()

        return box_type

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

    # display onos info
    # type == 1 -> text mode
    # type == 2 -> curses mode
    @classmethod
    def display_onos_info(cls, type):
        if type is 1:
            try:
                width = 60
                print BG_WHITE + "|%s|" % ('-' * width).ljust(width) + ENDC
                print BG_WHITE + '|' + BG_BLUEW + BOLD + \
                        ("{0:^" + str(width) + "}").format("CLI") + BG_WHITE + '|' + ENDC
                print BG_WHITE + "|%s|" % ('-' * width).ljust(width) + ENDC
            except:
                LOG.exception_err_write()

        elif type is 2:
            box_onos = curses.newwin(SYS.get_onos_line_count() + 2, MAIN_WIDTH, 1, 1)
            box_onos.box()

            try:
                status_text_OK = curses.color_pair(2)
                status_text_NOK = curses.color_pair(3)
                normal_text = curses.A_NORMAL

                box_onos.addstr(0, 18, ' CONTROL PLAN ', normal_text)

                i = 1
                for onos in SYS.onos_list.keys():
                    str_info = onos + ' ['
                    box_onos.addstr(i, 2, str_info)
                    str_status = (dict)(SYS.onos_list[onos])['ping_status']

                    if str_status is 'OK':
                        box_onos.addstr(i, 2 + len(str_info), str_status, status_text_OK)
                    else:
                        box_onos.addstr(i, 2 + len(str_info), str_status, status_text_NOK)

                    box_onos.addstr(i, 2 + len(str_info) + len(str_status), ']')

                    i += 1
            except:
                LOG.exception_err_write()

            return box_onos