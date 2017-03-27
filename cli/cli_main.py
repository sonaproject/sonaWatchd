#!/usr/bin/python
import readline
import curses
import threading
import time

from log_lib import LOG
from system_info import SYS
from config import CONFIG
from cli import CLI
from flow_trace import TRACE
from log_lib import USER_LOG
from screen import SCREEN

def main():
    # read config
    if not CONFIG.init_config(LOG):
        print 'read config fail...'
        exit()

    # set log
    LOG.set_default_log('sonawatched_err.log')

    # set cli log
    cli_log = USER_LOG()
    cli_log.set_log('sonawatched_cli.log', CONFIG.get_cli_log_rotate(), int(CONFIG.get_cli_log_backup()))
    CLI.set_cli_log(cli_log)

    # set trace log
    trace_log = USER_LOG()
    trace_log.set_log('sonawatched_trace.log', CONFIG.get_trace_log_rotate(), int(CONFIG.get_trace_log_backup()))
    TRACE.set_trace_log(trace_log)

    # read log option
    LOG.set_log_config()

    # inquiry onos info
    onos_info = SYS.inquiry_onos_info()

    # setting onos info
    SYS.set_onos_info(onos_info)

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
    SYS.set_onos_thr_flag(False)
    onos_thread.join()
    exit()

def check_onos_status():
    try:
        while SYS.get_onos_thr_flag():
            if SYS.get_onos_redraw_flag():
                onos_info = SYS.inquiry_onos_info()

                if SYS.changed_onos_info(onos_info) is True:
                    SCREEN.draw_system()

            time.sleep(1)
    except:
        LOG.exception_err_write()

def set_readline_opt():
    delims = readline.get_completer_delims().replace("-", "^")
    readline.set_completer_delims(delims)

    # mac OS
    if 'libedit' in readline.__doc__:
        readline.parse_and_bind("bind -e")
        readline.parse_and_bind("bind '\t' rl_complete")
    else:
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

        SCREEN.draw_system()
        SCREEN.draw_menu(menu_list, selected_menu_no)

        SYS.set_onos_redraw_flag(True)

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
                SYS.set_onos_redraw_flag(False)

                # ?? is it necessary?
                SCREEN.refresh_screen()
                SCREEN.screen_exit()

                SCREEN.display_header(menu_list[selected_menu_no - 1])

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

            SCREEN.draw_system()
            SCREEN.draw_menu(menu_list, selected_menu_no)

            SCREEN.refresh_screen()
            SYS.set_onos_redraw_flag(True)

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
