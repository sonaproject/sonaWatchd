# Copyright (c) 2017 by Telcoware kimjt
# All Rights Reserved.
# SONA Monitoring Solutions.

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import base64
import multiprocessing as multiprocess

from monitor.cmd_proc import CMD_PROC
from api.config import CONF
from api.sona_log import LOG

import urlparse
import json

class RestHandler(BaseHTTPRequestHandler):
    def do_HEAD(self, res_code):
        self.send_response(res_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        LOG.info('[CLI] res_code = ' + str(res_code))

    def do_GET(self):
        request_sz = int(self.headers["Content-length"])
        request_str = self.rfile.read(request_sz)
        request_obj = json.loads(request_str)

        LOG.info('[CLI] starting do_GET() ' + 'client-info = ' + str(self.client_address) + ' msg = ' + json.dumps(request_obj))

        ''' Present frontpage with user authentication. '''
        if self.headers.getheader('Authorization') == None:
            self.do_HEAD(401)
            self.wfile.write('no auth header received')

            LOG.info('[CLI] [SEND RES] no auth header received')
        elif not self.path.startswith('/command'):
            self.do_HEAD(404)
            self.wfile.write(self.path + ' not found')

            LOG.info('[CLI] [SEND RES] ' + self.path + ' not found')
        elif self.auth_pw(self.headers.getheader('Authorization')):
            res_body = CMD_PROC.parse_req(request_obj)

            self.do_HEAD(200)
            self.wfile.write(json.dumps(res_body))

            LOG.info('[CLR] [SEND RES] = ' + json.dumps(res_body))
        else:
            self.do_HEAD(401)
            self.wfile.write(self.headers.getheader('Authorization'))
            self.wfile.write('not authenticated')

            LOG.info('[CLI] [SEND RES] not authenticated')

    def auth_pw(self, cli_pw):
        id_pw_list = CONF.rest()['user_password']
        cli_pw = base64.b64decode(cli_pw)

        for id_pw in id_pw_list:
            if id_pw.strip() == cli_pw:
                return True

        return False

def run(handlerclass=HTTPServer, handler_class=RestHandler, port=int(CONF.rest()['rest_server_port'])):
    server_address = ("", port)
    httpd = handlerclass(server_address, handler_class)
    httpd.serve_forever()


def rest_server_start():
    rest_server_daemon = multiprocess.Process(name='rest_server', target=run)
    rest_server_daemon.daemon = True
    rest_server_daemon.start()
