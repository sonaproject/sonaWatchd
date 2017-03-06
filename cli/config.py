import ConfigParser

class Config():
    COMMAND_SECTION_NAME = 'command'
    COMMAND_OPT_KEY_NAME = 'option_list'

    config_file = 'config/cli_config.ini'
    config = ConfigParser.RawConfigParser()

    def init_config(self):
        # read config
        try:
            self.config.read(self.get_config_file_name())
        except:
            print self.config_file + ' read error'
            return False

    def get_key_list(self, section_name):
        return self.config.options(section_name)

    def get_value(self, section_name, key):
        return self.config.get(section_name, key)

    def get_config_file_name(self):
        return self.config_file

    def get_config_instance(self):
        return self.config
