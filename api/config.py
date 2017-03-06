# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import ConfigParser

class ConfReader(object):
    ConfMap = dict()

    def __init__(self):
        self.config = ConfigParser.ConfigParser()
        self.config.read("config/config.ini")
        self.__loadConfigMap()

    def __loadConfigMap(self):
        for sec in self.config.sections():
            for key,value in self.config.items(sec):
                # print 'key = ', key, 'Value = ', value
                keyDict = str(sec) + '_' + str(key)
                # print 'keyDict = ' + keyDict
                self.ConfMap[keyDict] = value

    def getValue(self, key):
        value = ''
        try:
            print ' Key = ', key
            value = self.ConfMap[key] 
        except KeyError as KE:
            print 'Key', KE , ' didn\'t found in configuration.'

        return value

class MyConf(object):
    obj = ConfReader()
