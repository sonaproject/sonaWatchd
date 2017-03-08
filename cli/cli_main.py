#!/usr/bin/python
from __future__ import division
import readline
from onos_info import ONOSInfo
from config import Config
from log_lib import LogLib

import curses
import threading
import time

# create instance
onos = ONOSInfo()
config = Config()

command_list = []
search_list = []

menu_list = ["CLI", "Flow Trace"]
selected_menu_no = 1
selected_sys = 'all'

onos_thr_flag = True
onos_redraw_flag = False

cli_ret_flag = False

def main():
    global onos
    global command_list
    global onos_check_flag
    global onos_thr_flag

    # use class method
    LogLib.set_log()

    # read config
    config.init_config()

    # inquiry onos info
    onos_info = onos.inquiry_onos_info()

    # setting onos info
    onos.set_onos_info(config, onos_info)

    # set command list
    command_list = config.get_key_list(config.COMMAND_SECTION_NAME)

    # set search list
    set_search_list()

    onos_thread = threading.Thread(target=check_onos_status)
    onos_thread.daemon = False
    onos_thread.start()

    # select input menu
    select_menu()

    # exit
    print 'Processing shutdown...'
    onos_thr_flag = False
    onos_thread.join()
    exit()

def check_onos_status():
    global onos
    global onos_redraw_flag
    global onos_thr_flag

    while onos_thr_flag:
        if onos_redraw_flag:
            onos_info = onos.inquiry_onos_info()

            if onos.changed_onos_info(onos_info) is True:
                box_onos = onos.display_onos_info(2)
                box_onos.refresh()

        time.sleep(10)

def draw_menu():
    global menu_list
    global selected_menu_no

    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    highlightText = curses.color_pair(1)
    normalText = curses.A_NORMAL

    box_type = curses.newwin(len(menu_list) + 2, 70, onos.get_onos_line_count() + 3, 1)
    box_type.box()

    box_type.addstr(0, 32, ' MENU ', normalText)

    for i in range(1, len(menu_list) + 1):
        if i is selected_menu_no:
            box_type.addstr(i, 2, str(i) + "." + menu_list[i - 1], highlightText)
        else:
            box_type.addstr(i, 2, str(i) + "." + menu_list[i - 1], normalText)

    return box_type

def send_trace(ip, condition):
    # req trace
    pass

def select_menu():
    global onos_redraw_flag
    global command_list
    global selected_menu_no
    global cli_ret_flag

    screen = curses.initscr()
    curses.noecho()
    curses.cbreak()
    curses.start_color()
    screen.keypad(1)
    curses.curs_set(0)

    screen.refresh()

    box_onos = onos.display_onos_info(2)
    box_onos.refresh()

    box_menu = draw_menu()
    box_menu.refresh()

    onos_redraw_flag = True

    x = screen.getch()

    while x != 27:
        if x == curses.KEY_DOWN:
            if selected_menu_no != len(menu_list):
                selected_menu_no += 1

        elif x == curses.KEY_UP:
            if selected_menu_no != 1:
                selected_menu_no -= 1

        elif x == ord("\n"):
            # stop timer
            onos_redraw_flag = False

            screen.refresh()
            curses.endwin()
            onos.display_onos_info(1)

            if (menu_list[selected_menu_no - 1]) == 'CLI':
                while 1:
                    # select_command (handling tab event)
                    cmd = select_cmd()
                    # send command
                    send_cmd(cmd)

                    if cmd == 'menu':
                        break
                    elif cmd == 'quit' or cmd == 'exit':
                        return
                    else:
                        while not cli_ret_flag:
                            time.sleep(1)

            elif (menu_list[selected_menu_no - 1]) == 'Flow Trace':
                ip = raw_input('Flow Trace> ip : ')
                condition = raw_input('Flow Trace> condition : ')

                send_trace(ip, condition)
                print 'result | ip = ' + ip + ', ' + 'condition = ' + condition

                cmd = raw_input('Flow Trace> menu or quit : ')
                if cmd == 'quit' or cmd == 'exit':
                    return


        box_onos = onos.display_onos_info(2)
        box_onos.refresh()

        box_menu = draw_menu()
        box_menu.refresh()

        screen.refresh()

        onos_redraw_flag = True

        x = screen.getch()

    curses.endwin()
    return

def check_timeout():
    global cli_ret_flag

    if cli_ret_flag:
        return

    print 'cmd timeout'
    cli_ret_flag = True

def send_cmd(cmd):
    global cli_ret_flag

    cli_ret_flag = False

    tmr = threading.Timer(3, check_timeout)
    tmr.start()

    """
    # if return comes
    cli_ret_flag = True
    # print result
    print "input command = " + cmd
    """

def display_cmd(sel_no):
    global command_list
    global onos

    try :
        """
        print '===================================================='

        for cmd in command_list:
            help = cmd + '\t\t-' + config.get_value(config.COMMAND_SECTION_NAME, cmd)

            if (config.get_config_instance().has_section(cmd)):
                help = help + '\t\toption = ' + config.get_value(cmd, config.COMMAND_OPT_KEY_NAME)
            print help
        """

        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
        highlightText = curses.color_pair(1)
        normalText = curses.A_NORMAL

        # make window
        box_cmd = curses.newwin(len(command_list) + 2, 70, onos.get_onos_line_count() + 3, 1)

        box_cmd.box()

        box_cmd.addstr(0, 40, 'MMC LIST', normalText)

        i = 1
        for cmd in command_list:
            if (sel_no is i):
                box_cmd.addstr(i, 2, cmd, highlightText)
            else:
                box_cmd.addstr(i, 2, cmd, normalText)

            box_cmd.addstr(i, 20, config.get_value(config.COMMAND_SECTION_NAME, cmd), normalText)

            if (config.get_config_instance().has_section(cmd)):
                box_cmd.addstr(i, 50, 'option = ' + config.get_value(cmd, config.COMMAND_OPT_KEY_NAME), normalText)

            i += 1

        return box_cmd
    except:
        pass

def select_cmd():
    global selected_sys

    # special processing
    delims = readline.get_completer_delims().replace("-", "^")
    readline.set_completer_delims(delims)
    delims = readline.get_completer_delims().replace(" ", "^")
    readline.set_completer_delims(delims)

    readline.parse_and_bind("tab:complete")
    readline.parse_and_bind('set editing-mode vi')
    readline.set_completer(complete)

    cmd = raw_input('CLI(' + selected_sys + ')> ')

    if cmd.startswith('sys'):
        selected_sys = (cmd.split(' '))[1]

    return cmd

def set_search_list():
    global search_list

    for cmd in command_list:
        search_list.append(cmd)

        if (config.get_config_instance().has_section(cmd)):
            opt_list = config.get_value(cmd, config.COMMAND_OPT_KEY_NAME)
            for opt in opt_list.split(','):
                search_list.append(cmd + ' ' + opt.strip())

    search_list.append('menu')
    search_list.append('quit')
    search_list.append('exit')
    search_list.append('sys all')
    for onos_name in onos.get_onos_list():
        search_list.append('sys ' + onos_name)

def complete(text, state):
    global search_list
    global command_list
    global onos

    for cmd in search_list:
        if cmd.startswith(text):
            if not state:
                return str(cmd)
            else:
                state -= 1


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print "Interrupted exit!!!"
    finally:
        pass
