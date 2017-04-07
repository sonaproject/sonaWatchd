import time

from log_lib import LOG
from flow_trace import TRACE

from asciimatics.widgets import Frame, ListBox, Layout, Divider, Text, \
    Button, Widget, Label
from asciimatics.scene import Scene
from asciimatics.screen import Screen
from asciimatics.exceptions import NextScene, StopApplication
from asciimatics.event import KeyboardEvent

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
menu_list = [("CLI", 1), ("Flow Trace", 2)]

class SCREEN():
    cli_flag = False
    quit_flag = False
    restart_flag = False

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

    @staticmethod
    def start_screen(screen, scene):
        scenes = [
            Scene([MenuListView(screen)], -1, name="Main"),
            Scene([FlowTraceView(screen)], -1, name="Flow Trace")
        ]

        screen.play(scenes, stop_on_resize=True, start_scene=scene)

    @classmethod
    def set_exit(cls):
        cls.quit_flag = True

class MenuListView(Frame):
    def __init__(self, screen):
        try:
            super(MenuListView, self).__init__(screen,
                                               screen.height * 7 // 10,
                                               screen.width * 7 // 10,
                                               hover_focus=True,
                                               title=" MENU ")

            self._screen = screen

            layout_test = Layout([100])
            self.add_layout(layout_test)
            layout_test.add_widget(Label(label="test"))

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
        except:
            LOG.exception_err_write()

    def process_event(self, event):
        if isinstance(event, KeyboardEvent):
            c = event.key_code

            # Stop on ESC
            if c == Screen.KEY_ESCAPE:
                SCREEN.set_exit()
                raise StopApplication("User terminated app")

            # press enter at list view
            if self._list_view._has_focus and c == 10:
                if self._list_view.value == 1:
                    SCREEN.cli_flag = True
                    raise StopApplication("User terminated app")
                elif self._list_view.value == 2:
                    raise NextScene("Flow Trace")

        return super(MenuListView, self).process_event(event)

    @staticmethod
    def _quit():
        SCREEN.set_exit()
        raise StopApplication("User pressed quit")

class FlowTraceView(Frame):
    def __init__(self, screen):
        try:
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
        except:
            LOG.exception_err_write()

    def process_event(self, event):
        if isinstance(event, KeyboardEvent):
            c = event.key_code

            # Stop on ESC
            if c == Screen.KEY_ESCAPE:
                SCREEN.set_exit()
                raise StopApplication("User terminated app")

        return super(FlowTraceView, self).process_event(event)

    def key_name(self, key):
        try:
            default_width = 10

            key = '* ' + key

            if len(key) < default_width:
                for i in range(default_width - len(key)):
                    key = key + ' '

            key = key + ' '
        except:
            LOG.exception_err_write()
        return key

    def reset(self):
        super(FlowTraceView, self).reset()

    def _ok(self):
        self.save()

    @staticmethod
    def _menu():
        raise NextScene("Main")

    @staticmethod
    def _quit():
        SCREEN.set_exit()
        raise StopApplication("User pressed quit")
