# Copyright (c) 2017 by Telcoware kimjt
# All Rights Reserved.
# SONA Monitoring Solutions.

import base64
import multiprocessing as multiprocess

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from monitor.cmd_proc import CMD_PROC
from api.config import CONF
from api.sona_log import LOG

import json


class RestHandler(BaseHTTPRequestHandler):
    def do_HEAD(self, res_code):
        self.send_response(res_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        LOG.info('[REST-SERVER] RESPONSE CODE = ' + str(res_code))

    def do_GET(self):
        request_sz = int(self.headers["Content-length"])
        request_str = self.rfile.read(request_sz)
        request_obj = json.loads(request_str)

        LOG.info('[REST-SERVER] CLIENT INFO = ' + str(self.client_address))
        LOG.info('[REST-SERVER] RECV BODY = ' + json.dumps(request_obj, sort_keys=True, indent=4))

        if self.headers.getheader('Authorization') == None:
            self.do_HEAD(401)
            self.wfile.write('no auth header received')

            LOG.info('[REST-SERVER] no auth header received')
        elif not self.path.startswith('/command'):
            self.do_HEAD(404)
            self.wfile.write(self.path + ' not found')

            LOG.info('[REST-SERVER] ' + self.path + ' not found')
        elif not CMD_PROC.exist_command(request_obj):
            self.do_HEAD(404)
            self.wfile.write('command not found')

            LOG.info('[REST-SERVER] ' + 'command not found')
        elif self.auth_pw(self.headers.getheader('Authorization')):
            res_body = CMD_PROC.parse_req(request_obj)

            self.do_HEAD(200)
            self.wfile.write(json.dumps(res_body))

            LOG.info('[REST-SERVER] RES BODY = ' + json.dumps(res_body, sort_keys=True, indent=4))
        else:
            self.do_HEAD(401)
            self.wfile.write(self.headers.getheader('Authorization'))
            self.wfile.write('not authenticated')

            LOG.info('[REST-SERVER] not authenticated')

    def auth_pw(self, cli_pw):
        id_pw_list = CONF.rest()['user_password']
        cli_pw = base64.b64decode(cli_pw)

        for id_pw in id_pw_list:
            if id_pw.strip() == cli_pw:
                LOG.info('[REST-SERVER] AUTH SUCCESS = ' + id_pw)
                return True

        LOG.info('[REST-SERVER] AUTH FAIL = ' + cli_pw)
        return False


# def run(handlerclass=HTTPServer, handler_class=RestHandler, port=int(CONF.rest()['rest_server_port'])):
def run():
    server_address = ("", int(CONF.rest()['rest_server_port']))
    httpd = HTTPServer(server_address, RestHandler)
    httpd.serve_forever()


def rest_server_start():
    LOG.info("--- REST Server Start --- ")
    rest_server_daemon = multiprocess.Process(name='rest_server', target=run)
    rest_server_daemon.daemon = True
    rest_server_daemon.start()

