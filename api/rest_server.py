# Copyright (c) 2017 by Telcoware kimjt
# All Rights Reserved.
# SONA Monitoring Solutions.

import json
import base64
from datetime import datetime
import multiprocessing as multiprocess

import monitor.cmd_proc as command

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from api.config import CONF
from api.sona_log import LOG

import sonatrace as trace


class RestHandler(BaseHTTPRequestHandler):
    # write buffer; 0: unbuffered, -1: buffering; rf) default rbufsize(rfile) is -1.
    wbufsize = -1

    def do_HEAD(self, res_code):
        self.send_response(res_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        LOG.info('[REST-SERVER] RESPONSE CODE = ' + str(res_code))

    def do_GET(self):
        # health check
        if self.path.startswith('/alive-check'):
            self.do_HEAD(200)
            self.wfile.write('ok\n')
            return

        if not self.authentication():
            self.do_HEAD(401)
            return
        else:
            if not self.headers.getheader('Content-Length'):
                self.do_HEAD(400)
                self.wfile.write('Bad Request, Content Length is 0\n')
                return
            else:
                request_size = int(self.headers.getheader("Content-Length"))
                request_string = self.rfile.read(request_size)
                request_obj = json.loads(request_string)

            LOG.info('[REST-SERVER] CLIENT INFO = ' + str(self.client_address))
            LOG.info('[REST-SERVER] RECV BODY = \n' + json.dumps(request_obj, sort_keys=True, indent=4))

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
                self.wfile.write(self.path + ' not found\n')

                LOG.info('[REST-SERVER] ' + self.path + ' not found')

    def do_POST(self):

        if not self.authentication():
            self.do_HEAD(401)
            return
        else:
            if self.path.startswith('/trace_request'):
                trace_mandatory_field = ['source_ip', 'destination_ip']
                trace_result_data = {}

                trace_condition_json = self.get_content()
                if not trace_condition_json:
                    return
                else:
                    if not all(x in dict(trace_condition_json['matchingfields']).keys() for x in trace_mandatory_field):
                        self.do_HEAD(400)
                        self.wfile.write('Not Exist Mandatory Attribute\n')
                        return
                    else:
                        self.do_HEAD(200)
                        self.wfile.write(str({'result': 'Success'}))

                try:
                    trace_result_data.update(trace.flow_trace(trace_condition_json['matchingfields']))
                except:
                    LOG.exception()

                trace_result_data['time'] = str(datetime.now())
                LOG.info(json.dumps(trace_result_data, sort_keys=True, indent=4))

                # TODO send trace result noti

            else:
                self.do_HEAD(404)
                self.wfile.write("Not Found path \"" + self.path + "\"\n")
                return

    def get_content(self):
        if not self.headers.getheader('content-length'):
            self.do_HEAD(400)
            self.wfile.write('Bad Request, Content Length is 0\n')
            LOG.info('[TRACE REST-S] Received No Data from %s', self.client_address)
            return False
        else:
            try:
                receive_data = json.loads(self.rfile.read(int(self.headers.getheader("content-length"))))
                LOG.info('[Trace Conditions] \n' + json.dumps(receive_data, sort_keys=True, indent=4))
                return receive_data
            except:
                LOG.exception()
                error_reason = 'Trace Request Json Data Parsing Error\n'
                self.do_HEAD(400)
                self.wfile.write(error_reason)
                LOG.info('[TRACE] %s', error_reason)
                return False


    def authentication(self):
        try:
            if not self.headers.getheader("authorization"):
                self.wfile.write('No Authorization Header\n')
                return False
            else:
                request_auth = self.headers.getheader("authorization")
                id_pw_list = CONF.rest()['user_password']

                try:
                    request_account = base64.b64decode(str(request_auth).split()[-1])

                    for id_pw in id_pw_list:
                        if id_pw.strip() == request_account:
                            LOG.info('[REST-SERVER] AUTH SUCCESS = %s, from %s', id_pw, self.client_address)
                            return True
                except:
                    LOG.exception()

                self.wfile.write('Request Authentication User ID or Password is Wrong \n')
                LOG.info('[REST-SERVER] AUTH FAIL = %s, from %s',
                         base64.b64decode(str(request_auth).split()[-1]), self.client_address)
                return False

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


