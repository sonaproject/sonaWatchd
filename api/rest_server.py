# Copyright (c) 2017 by Telcoware kimjt
# All Rights Reserved.
# SONA Monitoring Solutions.

import json
import base64
import multiprocessing as multiprocess

import monitor.cmd_proc as command

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from api.config import CONF
from api.sona_log import LOG
from watcherdb import DB


class RestHandler(BaseHTTPRequestHandler):
    def do_HEAD(self, res_code):
        self.send_response(res_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        LOG.info('[REST-SERVER] RESPONSE CODE = ' + str(res_code))

    def do_GET(self):
        # health check
        if self.path.startswith('/alive-check'):
            self.do_HEAD(200)
            self.wfile.write('ok')
            return

        request_sz = int(self.headers["Content-length"])
        request_str = self.rfile.read(request_sz)
        request_obj = json.loads(request_str)

        LOG.info('[REST-SERVER] CLIENT INFO = ' + str(self.client_address))
        LOG.info('[REST-SERVER] RECV BODY = \n' + json.dumps(request_obj, sort_keys=True, indent=4))

        if self.headers.getheader('Authorization') is None:
            self.do_HEAD(401)
            self.wfile.write('no auth header received')

            LOG.info('[REST-SERVER] no auth header received')

        elif self.auth_pw(self.headers.getheader('Authorization')):
            if self.path.startswith('/command'):
                try:
                    if command.exist_command(request_obj):
                        res_body = command.parse_command(request_obj)

                        self.do_HEAD(200)
                        self.wfile.write(json.dumps(res_body))

                        LOG.info('[REST-SERVER] RES BODY = \n%s',
                                 json.dumps(res_body, sort_keys=True, indent=4))
                    else:
                        self.do_HEAD(404)
                        self.wfile.write('command not found')

                        LOG.info('[REST-SERVER] ' + 'command not found')
                except:
                    LOG.exception()

            elif self.path.startswith('/regi'):
                try:
                    self.do_HEAD(200)

                    url = str(request_obj['url'])

                    res_body = command.regi_url(url, self.headers.getheader('Authorization'))

                    self.wfile.write(json.dumps(res_body))

                    LOG.info('[REST-SERVER] RES BODY = \n%s',
                             json.dumps(res_body, sort_keys=True, indent=4))
                except:
                    LOG.exception()

            elif self.path.startswith('/event_list'):
                try:
                    self.do_HEAD(200)

                    url = str(request_obj['url'])

                    res_body = command.get_event_list(url, self.headers.getheader('Authorization'))

                    self.wfile.write(json.dumps(res_body))

                    LOG.info('[REST-SERVER] RES BODY = \n%s',
                             json.dumps(res_body, sort_keys=True, indent=4))
                except:
                    LOG.exception()

            elif self.path.startswith('/unregi'):
                try:
                    self.do_HEAD(200)

                    url = str(request_obj['url'])

                    res_body = command.unregi_url(url)

                    self.wfile.write(json.dumps(res_body))

                    LOG.info('[REST-SERVER] RES BODY = \n%s',
                             json.dumps(res_body, sort_keys=True, indent=4))
                except:
                    LOG.exception()

            else:
                self.do_HEAD(404)
                self.wfile.write(self.path + ' not found')

                LOG.info('[REST-SERVER] ' + self.path + ' not found')

        else:
            self.do_HEAD(401)
            self.wfile.write(self.headers.getheader('Authorization'))
            self.wfile.write('not authenticated')

            LOG.info('[REST-SERVER] not authenticated')

    def auth_pw(self, cli_pw):
        try:
            id_pw_list = CONF.rest()['user_password']

            strBasic = 'Basic '
            if str(cli_pw).startswith(strBasic):
                cli_pw = cli_pw[len(strBasic):]

            cli_pw = base64.b64decode(cli_pw)

            for id_pw in id_pw_list:
                if id_pw.strip() == cli_pw:
                    LOG.info('[REST-SERVER] AUTH SUCCESS = ' + id_pw)
                    return True

            LOG.info('[REST-SERVER] AUTH FAIL = ' + cli_pw)

        except:
            LOG.exception()

        return False


def run():
    try:
        server_address = ("", int(CONF.rest()['rest_server_port']))
        httpd = HTTPServer(server_address, RestHandler)
        httpd.serve_forever()
    except:
        print 'Rest Server failed to start'
        LOG.exception()


def rest_server_start():
    LOG.info("--- REST Server Start --- ")

    rest_server_daemon = multiprocess.Process(name='rest_server', target=run)
    rest_server_daemon.daemon = True
    rest_server_daemon.start()


