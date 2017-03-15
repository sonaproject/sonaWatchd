# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import ConfigParser

DEFAULT_CONF_FILE = "config/config.ini"


class ConfReader:
    conf_map = dict()

    def __init__(self):
        self.config = ConfigParser.ConfigParser()
        self.config.read(self.__conf_file(None))
        self.__load_config_map()

    def __load_config_map(self):
        for section in self.config.sections():
            self.conf_map[section] = {key: value for key, value in self.config.items(section)}


    @staticmethod
    def __list_opt(value):
        return list(str(value).replace(" ", "").split(','))

    @staticmethod
    def __conf_file(file_name=None):
        if file_name is not None:
            return file_name
        else:
            return DEFAULT_CONF_FILE

    def base(self):
        value = dict()
        try:
            value['pidfile'] = str(self.conf_map['BASE']['pidfile'])
            value['log_file_name'] = str(self.conf_map['BASE']['log_file_name'])
            value['log_rotate_time'] = str(self.conf_map['BASE']['log_rotate_time'])
            value['log_backup_count'] = int(self.conf_map['BASE']['log_backup_count'])
            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def watchdog(self):
        value = dict()
        try:
            value['system_check_interval'] = int(self.conf_map['WATCHDOG']['system_check_interval'])
            value['check_command'] = str(self.conf_map['WATCHDOG']['check_command'])
            value['check_timeout'] = int(self.conf_map['WATCHDOG']['check_timeout'])
            value['check_retry'] = int(self.conf_map['WATCHDOG']['check_retry'])
            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def ssh_conn(self):
        value = dict()
        try:
            value['ssh_req_timeout'] = int(self.conf_map['SSH_CONN']['ssh_req_timeout'])
            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def rest(self):
        value = dict()
        try:
            value['rest_server_port'] = int(self.conf_map['REST']['rest_server_port'])
            value['user_password'] = self.__list_opt(self.conf_map['REST']['user_password'])
            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def onos(self):
        value = dict()
        try:
            value['list'] = self.__list_opt(self.conf_map['ONOS']['list'])
            value['app_list'] = self.__list_opt(self.conf_map['ONOS']['app_list'])
            value['system_account'] = self.__list_opt(self.conf_map['ONOS']['system_account'])
            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def xos(self):
        value = dict()
        try:
            value['list'] = self.__list_opt(self.conf_map['XOS']['list'])
            value['system_account'] = self.__list_opt(self.conf_map['XOS']['system_account'])
            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def k8s(self):
        value = dict()
        try:
            value['list'] = self.__list_opt(self.conf_map['Kubernetes']['list'])
            value['system_account'] = self.__list_opt(self.conf_map['Kubernetes']['system_account'])
            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def openstack_node(self):
        value = dict()
        try:
            value['gateway_list'] = self.__list_opt(self.conf_map['OPENSTACK_NODE']['gateway_list'])
            value['system_account'] = self.__list_opt(self.conf_map['OPENSTACK_NODE']['system_account'])
            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def get_pid_file(self):
        try:
            return str(self.conf_map['BASE']['pidfile'])
        except KeyError as KE:
            return dict({'fail': KE})

CONF = ConfReader()
