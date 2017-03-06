import ConfigParser
import curses

class ONOSInfo():
    # key = onos_name
    # value = info_dic, it contains ip, conn state, app list & status...
    onos_list = {}

    def set_onos_info(self, config, onos_info):
        try:
            onos_dtl_list = {}
            onos_app_list = {}

            # read app list
            apps_list = config.get_value('onos', 'app_list')

            # examples
            for app in apps_list.split(','):
                onos_app_list[app.strip()] = 'ok'

            onos_dtl_list['ip'] = '10.10.2.66'
            onos_dtl_list['ping_status'] = 'ok'
            onos_dtl_list['app'] = onos_app_list

            self.onos_list['onos1'] = onos_dtl_list

            return True
        except:
            return False

    # inquery onos info
    def inquiry_onos_info(self):
        try:
            onos_info = ''

            # parsing & set data

            return onos_info
        except:
            # except handling
            return False

    def get_onos_line_count(self):
        # calc line count
        line_count = 0
        for onos in self.onos_list.keys():
            line_count = 1 + len(((self.onos_list[onos])['app']).keys())

        return line_count

    # display onos info
    def display_onos_info(self):
        try:
            # example
            """
            for onos in self.onos_list.keys():
                print 'onos_name = [' + onos + '] onos_ip = [' + (dict)(self.onos_list[onos])['ip'] + '] ping = [' + (dict)(self.onos_list[onos])['ping_status'] + ']'
                for app in (dict)((self.onos_list[onos])['app']).keys():
                    print '\t' + app + ' [' + (dict)((self.onos_list[onos])['app'])[app] + ']'
            """

            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
            highlightText = curses.color_pair(1)
            normalText = curses.A_NORMAL

            # make window
            box_onos = curses.newwin(self.get_onos_line_count() + 2, 90, 1, 1)
            box_onos.box()

            box_onos.addstr(0, 40, 'ONOS INFO', normalText)

            i = 1
            for onos in self.onos_list.keys():
                box_onos.addstr(i, 2, 'onos_name = [' + onos + '] onos_ip = [' + (dict)(self.onos_list[onos])['ip'] + '] ping = [' + (dict)(self.onos_list[onos])['ping_status'] + ']', normalText)
                i += 1

                for app in (dict)((self.onos_list[onos])['app']).keys():
                    box_onos.addstr(i, 10, app + ' [' + (dict)((self.onos_list[onos])['app'])[app] + ']', normalText)
                    i += 1

            return box_onos
        except:
            return False
