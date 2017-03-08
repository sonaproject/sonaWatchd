import ConfigParser
import curses

class ONOSInfo():
    # key = onos_name
    # value = info_dic, it contains ip, conn state, app list & status...
    onos_list = {}

    def set_onos_info(self, config, onos_info):
        try:
            onos_dtl_list = {}

            # read app list
            """
            onos_app_list = {}

            apps_list = config.get_value('onos', 'app_list')

            # examples
            for app in apps_list.split(','):
                onos_app_list[app.strip()] = 'ok'

            onos_dtl_list['app'] = onos_app_list
            """

            # sample data
            onos_dtl_list['ip'] = '10.10.2.66'
            onos_dtl_list['ping_status'] = 'ok'

            self.onos_list['onos1'] = onos_dtl_list

            onos_dtl_list['ip'] = '10.10.2.67'
            onos_dtl_list['ping_status'] = 'ok'

            self.onos_list['onos2'] = onos_dtl_list

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

    def get_onos_list(self):
        return self.onos_list.keys()

    def get_onos_line_count(self):
        # calc line count
        line_count = 0
        for onos in self.onos_list.keys():
            line_count += 1

        return line_count

    def changed_onos_info(self, new_info):
        # if changed : return true
        return True

    # display onos info
    # type == 1 -> text mode
    # type == 2 -> curses mode
    def display_onos_info(self, type):

        # make window
        box_onos = curses.newwin(self.get_onos_line_count() + 2, 70, 1, 1)

        try:
            if type is 1:
                print '====================================================================='
                for onos in self.onos_list.keys():
                    # must check status using app state
                    print 'onos_name = [' + onos + '] onos_ip = [' + (dict)(self.onos_list[onos])['ip'] + '] status = [' + (dict)(self.onos_list[onos])['ping_status'] + ']'
                print '====================================================================='

            elif type is 2:
                curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
                highlightText = curses.color_pair(1)
                normalText = curses.A_NORMAL

                box_onos.box()

                box_onos.addstr(0, 28, ' CONTROL PLAN ', normalText)

                i = 1
                for onos in self.onos_list.keys():
                    box_onos.addstr(i, 2, 'onos_name = [' + onos + '] onos_ip = [' + (dict)(self.onos_list[onos])['ip'] + '] ping = [' + (dict)(self.onos_list[onos])['ping_status'] + ']', normalText)
                    i += 1

                return box_onos

        except:
            return box_onos

