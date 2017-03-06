#!/usr/bin/python
from __future__ import division
import readline
from onos_info import ONOSInfo
from config import Config

import curses
import curses.textpad
from math import *

onos = ONOSInfo()
config = Config()
command_list = []

def main():
    global command_list

    # read config
    config.init_config()

    # inquiry onos info
    onos_info = onos.inquiry_onos_info()

    # setting onos info
    onos.set_onos_info(config, onos_info)

    # set command list
    command_list = config.get_key_list(config.COMMAND_SECTION_NAME)

    # select input type
    select_cli_gui()

    # display onos info
    # onos.display_onos_info

    # display command & help
    display_cmd(0)

    # select system
    select_onos()

    # select_command (handling tab event)
    cmd = select_cmd()

    # send command
    send_cmd(cmd)

def select_cli_gui():
    global command_list

    screen = curses.initscr()
    curses.noecho()
    curses.cbreak()
    curses.start_color()
    screen.keypad(1)
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    highlightText = curses.color_pair(1)
    normalText = curses.A_NORMAL
    screen.border(0)
    curses.curs_set(0)

    box_onos = onos.display_onos_info()
    box_mmc = display_cmd(0)

    max_row = 2
    box_type = curses.newwin(max_row + 2, 90, len(command_list) + onos.get_onos_line_count() + 5, 1)
    box_type.box()

    box_type.addstr(0, 40, 'MENU TYPE', normalText)

    strings = ["CLI", "GUI"]
    row_num = len(strings)

    pages = int(ceil(row_num / max_row))
    position = 1
    page = 1
    for i in range(1, max_row + 1):
        if row_num == 0:
            box_type.addstr(1, 1, "There aren't strings", highlightText)
        else:
            if (i == position):
                box_type.addstr(i, 2, str(i) + " - " + strings[i - 1], highlightText)
            else:
                box_type.addstr(i, 2, str(i) + " - " + strings[i - 1], normalText)
            if i == row_num:
                break

    screen.refresh()
    box_type.refresh()
    box_onos.refresh()
    box_mmc.refresh()

    x = 1
    # x = screen.getch()
    while x != 27:
        if x == curses.KEY_DOWN:
            if page == 1:
                if position < i:
                    position = position + 1
                else:
                    if pages > 1:
                        page = page + 1
                        position = 1 + (max_row * (page - 1))
            elif page == pages:
                if position < row_num:
                    position = position + 1
            else:
                if position < max_row + (max_row * (page - 1)):
                    position = position + 1
                else:
                    page = page + 1
                    position = 1 + (max_row * (page - 1))
        if x == curses.KEY_UP:
            if page == 1:
                if position > 1:
                    position = position - 1
            else:
                if position > (1 + (max_row * (page - 1))):
                    position = position - 1
                else:
                    page = page - 1
                    position = max_row + (max_row * (page - 1))


        if x == ord("\n") and row_num != 0:
            if (strings[position - 1]) == 'CLI':
                curses.endwin()
                return strings[position - 1]
            elif (strings[position - 1]) == 'GUI':
                """

                mmc_no = 1
                box_mmc = display_cmd(mmc_no)
                screen.addstr(30, 3, "YOU SELECTED GUI")
                box_mmc.refresh()

                x = screen.getch()
                while x != 27:
                    if x == curses.KEY_DOWN:
                        if mmc_no != len(command_list):
                            mmc_no += 1
                    if x == curses.KEY_UP:
                        if mmc_no > 1:
                            mmc_no -= 1

                    box_mmc = display_cmd(mmc_no)
                    box_mmc.refresh()

                    if x == ord("\n"):
                        screen.addstr(30, 3, "YOU SELECTED MMC = " + str(mmc_no) + "." + command_list[mmc_no - 1] + "                  ")

                    x = screen.getch()
                curses.endwin()
                exit()
                """


        screen.border(0)
        box_type.border(0)

        box_type.addstr(0, 40, 'MENU TYPE', normalText)

        for i in range(1 + (max_row * (page - 1)), max_row + 1 + (max_row * (page - 1))):
            if row_num == 0:
                box_type.addstr(1, 1, "There aren't strings", highlightText)
            else:
                if (i + (max_row * (page - 1)) == position + (max_row * (page - 1))):
                    box_type.addstr(i - (max_row * (page - 1)), 2, str(i) + " - " + strings[i - 1], highlightText)
                else:
                    box_type.addstr(i - (max_row * (page - 1)), 2, str(i) + " - " + strings[i - 1], normalText)
                if i == row_num:
                    break

        box_onos = onos.display_onos_info()
        box_mmc = display_cmd(0)

        screen.refresh()
        box_type.refresh()
        box_onos.refresh()
        box_mmc.refresh()

        x = screen.getch()

    curses.endwin()
    exit()

def send_cmd(cmd):
    print "input command = " + cmd


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

        """
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
        highlightText = curses.color_pair(1)
        normalText = curses.A_NORMAL

        # make window
        box_cmd = curses.newwin(len(command_list) + 2, 90, onos.get_onos_line_count() + 3, 1)
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
        """

        normalText = curses.A_NORMAL

        box_cmd = curses.newwin(len(command_list) + 2, 90, onos.get_onos_line_count() + 3, 1)
        box_cmd.box()
        box_cmd.addstr(0, 40, 'MMC LIST', normalText)

        box1 = curses.textpad.Textbox(box_cmd, insert_mode = True)
        a1 = box1.edit()
        curses.flash()

        box_cmd.addstr(1, 1, a1.encode('utf-8'))
        box_cmd.refresh()
        box_cmd.getch()

        return box_cmd

    except:
        pass

def select_onos():
    pass

def select_cmd():
    # special processing
    delims = readline.get_completer_delims().replace("-", "^")
    readline.set_completer_delims(delims)
    delims = readline.get_completer_delims().replace(" ", "^")
    readline.set_completer_delims(delims)

    readline.parse_and_bind("tab:complete")
    readline.parse_and_bind('set editing-mode vi')
    readline.set_completer(complete)

    cmd = raw_input('Enter command: ')
    return cmd

def complete(text, state):
    global command_list

    search_list = []
    for cmd in command_list:
        search_list.append(cmd)

        if (config.get_config_instance().has_section(cmd)):
            opt_list = config.get_value(cmd, config.COMMAND_OPT_KEY_NAME)
            for opt in opt_list.split(','):
                search_list.append(cmd + ' ' + opt.strip())

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

