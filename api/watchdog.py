# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import logging
from config import ConfReader

LOGFILE = '/tmp/sonawatcher.log'
logging.basicConfig(filename=LOGFILE,level=logging.DEBUG)


def temp():
    logging.error("kjt -------2 %s", ConfReader.rest())
    logging.error("kjt -------2 %s", ConfReader.openstack_node())
