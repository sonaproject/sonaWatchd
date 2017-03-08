# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import ConfigParser

DEFAULT_CONF_FILE = "config/config.ini"


class ConfReader:
    conf_map = dict()

    def __init__(cls, config_file=None):
        cls.config = ConfigParser.ConfigParser()
        cls.config.read(cls.__conf_file(config_file))
        cls.__load_config_map()

    def __load_config_map(self):
        for section in self.config.sections():
            self.conf_map[section] = {key: value for key, value in self.config.items(section)}

    @classmethod
    def base(cls):
        value = dict()
        try:
            value['pidfile'] = str(cls.conf_map['BASE']['pidfile'])
            value['log_prefix'] = str(cls.conf_map['BASE']['log_prefix'])
            value['log_format'] = str(cls.conf_map['BASE']['log_format'])
            return value
        except KeyError as KE:
            return

    @classmethod
    def watchdog(cls):
        value = dict()
        try:
            value['system_check_interval'] = int(cls.conf_map['WATCHDOG']['system_check_interval'])
            value['check_command'] = str(cls.conf_map['WATCHDOG']['check_command'])
            value['check_timeout'] = int(cls.conf_map['WATCHDOG']['check_timeout'])
            value['check_retry'] = int(cls.conf_map['WATCHDOG']['check_retry'])
            return value
        except KeyError as KE:
            return

    @classmethod
    def ssh_conn(cls):
        value = dict()
        try:
            value['ssh_req_timeout'] = int(cls.conf_map['SSH_CONN']['ssh_req_timeout'])
            return value
        except KeyError as KE:
            return

    @classmethod
    def rest(cls):
        value = dict()
        try:
            value['user_passwd'] = cls.__list_opt(cls.conf_map['REST']['user_passwd'])
            value['rest_server_port'] = int(cls.conf_map['REST']['rest_server_port'])
            return value
        except KeyError as KE:
            return

    @classmethod
    def onos(cls):
        value = dict()
        try:
            value['list'] = cls.__list_opt(cls.conf_map['ONOS']['list'])
            value['app_list'] = cls.__list_opt(cls.conf_map['ONOS']['app_list'])
            return value
        except KeyError as KE:
            return

    @classmethod
    def XOS(cls):
        value = dict()
        try:
            value['list'] = cls.__list_opt(cls.conf_map['XOS']['list'])
            return value
        except KeyError as KE:
            return

    @classmethod
    def k8s(cls):
        value = dict()
        try:
            value['list'] = cls.__list_opt(cls.conf_map['Kubernetes']['list'])
            return value
        except KeyError as KE:
            return

    @classmethod
    def openstack_node(cls):
        value = dict()
        try:
            value['gateway_list'] = cls.__list_opt(cls.conf_map['OPENSTACK_NODE']['gateway_list'])
            value['username'] = str(cls.conf_map['OPENSTACK_NODE']['username'])
            return value
        except KeyError as KE:
            return

    @classmethod
    def pid_file(cls):
        try:
            return str(cls.conf_map['BASE']['pidfile'])
        except KeyError as KE:
            return

    @staticmethod
    def __list_opt(value):
        return list(str(value).replace(" ", "").split(','))

    @staticmethod
    def __conf_file(file_name):
        if file_name is not None:
            return file_name
        else:
            return DEFAULT_CONF_FILE
