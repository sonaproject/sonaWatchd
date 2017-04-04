# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import sqlite3

from sona_log import LOG
from config import CONF


class DB(object):
    def __init__(self):
        self._conn = self.connection()
        self._conn.commit()

    @staticmethod
    def connection():
        try:
            conn = sqlite3.connect(CONF.base()['db_file'])
            conn.isolation_level = None
            return conn
        except:
            LOG.exception()
            exit(1)

    @classmethod
    def db_cursor(cls):
        return cls.connection().cursor()

    @classmethod
    def db_initiation(cls):
        LOG.info("--- Initiating SONA DB ---")
        init_sql = ['CREATE TABLE t_status(item text primary key, date, data)']

        for sql in init_sql:
            sql_rt = cls.sql_execute(sql)

            if "already exist" in sql_rt:
                table_name = sql_rt.split()[1]
                LOG.info("\'%s\' table already exist. Delete all tuple of this table...", table_name)
                sql = 'DELETE FROM ' + table_name
                sql_rt = cls.sql_execute(sql)
                if sql_rt != '':
                    LOG.info("DB %s table initiation fail", table_name)
                    exit(1)

    @classmethod
    def sql_execute(cls, sql):
        try:
            with cls.connection() as conn:
                conn.cursor().execute(sql)
                conn.commit()
            return ''
        except sqlite3.OperationalError, err:
            return err.message
        except:
            LOG.exception()


DB_CONN = DB().connection()
