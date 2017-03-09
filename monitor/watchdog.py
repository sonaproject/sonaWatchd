# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

from api.config import CONF
from api.sona_log import LOG


def temp():
    try:
        LOG.info("kjt --1-- test")
    except:
        LOG.exception()
