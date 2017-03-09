# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

from api.config import CONF
from api.sona_log import LOG


def temp():
    LOG.info("kjt ----- 1 %s", CONF.base()['log_file_name'])
