# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

from api.config import CONF
from api.sona_log import LOG

import mmap

def temp():
    try:
        LOG.info("kjt --1-- %s", CONF.watchdog())
    except:
        LOG.exception()

def make_file():
    try:
        with open("/home/hs/Projects/sonaWatchd/monitor/hello.txt", "wb") as f:
            f.write("Hello SONA1!\n")
            f.write("Hello Python1!\n")
            f.write("Hello SONA2!\n")
            f.write("Hello Python2!\n")
            f.write("Hello SONA3!\n")
            f.write("Hello Python3!\n")

            f.flush()
            f.close()
    except:
        LOG.exception()