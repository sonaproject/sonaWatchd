#!/usr/bin/python
import readline
import curses
import threading
import time

from log_lib import LOG
from onos_info import ONOS
from config import CONFIG
from cli import CLI
from trace import TRACE
from screen import SCREEN

def main():
    # set log
    LOG.set_log()

    # read config
    CONFIG.init_config(LOG)

    # read log option
    LOG.set_log_config()

    # inquiry onos info
    onos_info = ONOS.inquiry_onos_info()

    # setting onos info
    ONOS.set_onos_info(onos_info)

    # set command list
    CLI.set_cmd_list()

    # set trace cond list
    TRACE.set_cnd_list()

    # set search list
    CLI.set_search_list()
    TRACE.set_search_list()

    # create onos check thread
    onos_thread = threading.Thread(target=check_onos_status)
    onos_thread.daemon = False
    onos_thread.start()

    set_readline_opt()

    # select input menu
    select_menu()

    # exit
    print 'Processing shutdown...'
    ONOS.set_onos_thr_flag(False)
    onos_thread.join()
    exit()

def check_onos_status():
    try:
        while ONOS.get_onos_thr_flag():
            if ONOS.get_onos_redraw_flag():
                onos_info = ONOS.inquiry_onos_info()

                if ONOS.changed_onos_info(onos_info) is True:
                    SCREEN.draw_onos()

            time.sleep(1)
    except:
        LOG.exception_err_write()

def set_readline_opt():
    # special processing
    delims = readline.get_completer_delims().replace("-", "^")
    readline.set_completer_delims(delims)
    #delims = readline.get_completer_delims().replace(" ", "^")
    #readline.set_completer_delims(delims)

    readline.parse_and_bind("tab:complete")
    readline.parse_and_bind('set editing-mode vi')

def is_menu(cmd):
    if cmd == 'menu':
        return True

    return False

def is_exit(cmd):
    if cmd == 'quit' or cmd == 'exit':
        return True

    return False

def select_menu():
    menu_list = ["CLI", "Flow Trace"]

    selected_menu_no = 1

    try:
        SCREEN.set_screen()

        SCREEN.draw_onos()
        SCREEN.draw_menu(menu_list, selected_menu_no)

        ONOS.set_onos_redraw_flag(True)

        x = SCREEN.get_ch()

        while x != 27:
            if x == curses.KEY_DOWN:
                if selected_menu_no != len(menu_list):
                    selected_menu_no += 1

            elif x == curses.KEY_UP:
                if selected_menu_no != 1:
                    selected_menu_no -= 1

            elif x == ord("\n"):
                # stop timer
                ONOS.set_onos_redraw_flag(False)

                # ?? is it necessary?
                SCREEN.refresh_screen()
                SCREEN.screen_exit()

                SCREEN.display_onos_info(1)

                if (menu_list[selected_menu_no - 1]) == 'CLI':
                    readline.set_completer(CLI.pre_complete_cli)

                    while True:
                        # select_command (handling tab event)
                        cmd = CLI.input_cmd()

                        if is_menu(cmd):
                            break
                        elif is_exit(cmd):
                            return
                        else:
                            # send command
                            CLI.send_cmd(cmd)

                            while not CLI.get_cli_ret_flag():
                                time.sleep(1)

                elif (menu_list[selected_menu_no - 1]) == 'Flow Trace':
                    readline.set_completer(complete_dummy)

                    ip, condition = TRACE.imput_trace()

                    print 'result | ip = ' + ip + ', ' + 'Condition = ' + condition

                    TRACE.send_trace(ip, condition)

                    while True:
                        cmd = raw_input('Flow Trace> menu or quit : ')
                        if is_exit(cmd):
                            return
                        elif is_menu(cmd):
                            break
                        else:
                            print '[' + cmd + '] invalid command.'

            SCREEN.draw_onos()
            SCREEN.draw_menu(menu_list, selected_menu_no)

            SCREEN.refresh_screen()
            ONOS.set_onos_redraw_flag(True)

            x = SCREEN.get_ch()

        curses.endwin()
    except:
        LOG.exception_err_write()

def complete_dummy(text, state):
    pass

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        LOG.exception_err_write()

