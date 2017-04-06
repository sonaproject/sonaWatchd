#!/usr/bin/python
import os
import time
import threading
import readline

from log_lib import LOG
from system_info import SYS
from config import CONFIG
from cli import CLI
from flow_trace import TRACE
from log_lib import USER_LOG
from screen import SCREEN

from asciimatics.widgets import Frame, ListBox, Layout, Divider, Text, \
    Button, Widget, Label
from asciimatics.scene import Scene
from asciimatics.screen import Screen
from asciimatics.exceptions import ResizeScreenError, NextScene, StopApplication
from asciimatics.event import KeyboardEvent

# listview instance
# for global shortcut
list_ins = None

quit_flag = False
menu_list = [("CLI", 1), ("Flow Trace", 2)]

def main():
    try:
        from asciimatics.scene import Scene
    except:
        print "asciimatics library is not installed."
        print 'command execution \'sudo pip install asciimatics\''
        return

    # add for readline bug fix
    os.unsetenv('LINES')
    os.unsetenv('COLUMNS')

    # read config
    if not CONFIG.init_config(LOG):
        print 'read config fail...'
        return

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

    # create onos check thread
    onos_thread = threading.Thread(target=check_onos_status)
    onos_thread.daemon = False
    onos_thread.start()

    set_readline_opt()

    # select input menu
    call_main()

    # exit
    print 'Processing shutdown...'
    SYS.set_onos_thr_flag(False)
    onos_thread.join()

    return

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

class MenuListView(Frame):
    cur_menu = -1

    def __init__(self, screen):
        super(MenuListView, self).__init__(screen,
                                           screen.height * 7 // 10,
                                           screen.width * 7 // 10,
                                           hover_focus=True,
                                           title=" MENU ")

        # Create the form for displaying the list of contacts.
        self._list_view = ListBox(
            Widget.FILL_FRAME,
            menu_list,
            name="LIST_MENU",
            label="TEST LABEL")
        layout = Layout([100], fill_frame=True)
        self.add_layout(layout)
        layout.add_widget(self._list_view)
        layout.add_widget(Divider())
        layout2 = Layout([1])
        self.add_layout(layout2)
        layout2.add_widget(Button("Quit", self._quit), 0)
        self.fix()

    def reset_cur_menu(self):
        self.cur_menu = -1

    def select_menu(self):
        if self.cur_menu == self._list_view.value:
            return

        self.cur_menu = self._list_view.value

        if self._list_view.value == 1:
            raise StopApplication("User pressed quit")
        elif self._list_view.value == 2:
            raise NextScene("Flow Trace")

    def clear_data(self):
        self._list_view.options = menu_list

    @staticmethod
    def _quit():
        set_exit()
        raise StopApplication("User pressed quit")

class FlowTraceView(Frame):
    def __init__(self, screen):
        super(FlowTraceView, self).__init__(screen,
                                            screen.height * 7 // 10,
                                            screen.width * 7 // 10,
                                            hover_focus=True,
                                            title=" FLOW TRACE ",
                                            reduce_cpu=True)

        layout_l2_title = Layout([20,3,20])
        self.add_layout(layout_l2_title)

        layout_l2_title.add_widget(Label(label=''), 1)
        layout_l2_title.add_widget(Divider(height=2), 0)
        layout_l2_title.add_widget(Label(label=' L2'), 1)
        layout_l2_title.add_widget(Divider(height=2), 2)
        layout_l2_title.add_widget(Label(label=''), 1)

        i = 0
        for key, value in TRACE.trace_l2_cond_list:
            if i % 2 == 0:
                layout_l2 = Layout([1, 35, 3, 35, 1])
                self.add_layout(layout_l2)

                layout_l2.add_widget(Text(self.key_name(key), value), 1)
            else:
                layout_l2.add_widget(Text(self.key_name(key), value), 3)

            i = i + 1

        layout_l3_title = Layout([20, 3, 20])
        self.add_layout(layout_l3_title)

        layout_l3_title.add_widget(Label(label=''), 1)
        layout_l3_title.add_widget(Divider(height=2), 0)
        layout_l3_title.add_widget(Label(label=' L3'), 1)
        layout_l3_title.add_widget(Divider(height=2), 2)
        layout_l3_title.add_widget(Label(label=''), 1)

        i = 0
        for key, value in TRACE.trace_l3_cond_list:
            if i % 2 == 0:
                layout_l3 = Layout([1, 35, 3, 35, 1])
                self.add_layout(layout_l3)

                layout_l3.add_widget(Text(self.key_name(key), value), 1)
            else:
                layout_l3.add_widget(Text(self.key_name(key), value), 3)

            i = i + 1

        layout_dummy = Layout([1], fill_frame=True)
        self.add_layout(layout_dummy)

        layout_btn = Layout([1, 3, 3, 3, 3])
        self.add_layout(layout_btn)
        layout_btn.add_widget(Divider(), 0)
        layout_btn.add_widget(Divider(), 1)
        layout_btn.add_widget(Divider(), 2)
        layout_btn.add_widget(Divider(), 3)
        layout_btn.add_widget(Divider(), 4)
        layout_btn.add_widget(Button("Start Trace", self._ok), 1)
        layout_btn.add_widget(Button("Clear All", self.reset), 2)
        layout_btn.add_widget(Button("Menu", self._menu), 3)
        layout_btn.add_widget(Button("Quit", self._quit), 4)

        self.fix()

    def key_name(self, key):
        default_width = 10

        key = '* ' + key

        if len(key) < default_width:
            for i in range(default_width - len(key)):
                key = key + ' '

        return key

    def reset(self):
        super(FlowTraceView, self).reset()

    def _ok(self):
        self.save()

    @staticmethod
    def _menu():
        global list_ins

        MenuListView.reset_cur_menu(list_ins)
        raise NextScene("Main")

    @staticmethod
    def _quit():
        set_exit()
        raise StopApplication("User pressed quit")

def global_shortcuts(event):
    global list_ins
    if isinstance(event, KeyboardEvent):
        c = event.key_code

        # Stop on ESC
        if c == -1:
            set_exit()
            raise StopApplication("User terminated app")

        # press enter
        if c == 10:
            MenuListView.select_menu(list_ins)

def start_screen(screen, scene):
    global list_ins

    list_ins = MenuListView(screen)

    scenes = [
        Scene([list_ins], -1, name="Main"),
        Scene([FlowTraceView(screen)], -1, name="Flow Trace")
    ]

    screen.play(scenes, stop_on_resize=True, start_scene=scene, unhandled_input=global_shortcuts)



def complete_dummy(text, state):
    pass

def call_cli():
    SCREEN.display_header('CLI')

    readline.set_completer(CLI.pre_complete_cli)

    while True:
        # mac OS
        if 'libedit' in readline.__doc__:
            CLI.modify_flag = True
            CLI.save_buffer = readline.get_line_buffer()

        # select_command (handling tab event)
        cmd = CLI.input_cmd()

        if is_menu(cmd):
            return
        elif is_exit(cmd):
            set_exit()
            return
        else:
            # send command
            CLI.send_cmd(cmd)

            while not CLI.get_cli_ret_flag():
                time.sleep(1)

def set_exit():
    global quit_flag
    quit_flag = True

def call_main():
    global quit_flag

    last_scene = None
    while True:
        try:
            # for cli_exit
            if quit_flag:
                return

            Screen.wrapper(start_screen, catch_interrupt=True, arguments=[last_scene])

            if quit_flag:
                return
            else:
                call_cli()

        except ResizeScreenError as e:
            last_scene = e.scene
            LOG.exception_err_write()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        LOG.exception_err_write()