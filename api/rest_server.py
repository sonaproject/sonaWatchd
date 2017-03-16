# Copyright (c) 2017 by Telcoware kimjt
# All Rights Reserved.
# SONA Monitoring Solutions.

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import base64
import multiprocessing as multiprocess

from monitor.cmd_proc import CMD_PROC
import urlparse

key = base64.b64encode("admin:admin")

func_map = {'dis-resource': CMD_PROC.proc_dis_resource,
            'dis-onos': CMD_PROC.proc_dis_onos,
            'dis-log': CMD_PROC.proc_dis_log }

class RestHandler(BaseHTTPRequestHandler):
    ''' Main class to present webpages and authentication. '''
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        global key

        qs = {}
        res_body = {}
        cmd = ''
        system = ''
        param = ''

        ''' Present frontpage with user authentication. '''
        if self.headers.getheader('Authorization') == None:
            self.do_AUTHHEAD()
            self.wfile.write('no auth header received')
        elif self.headers.getheader('Authorization') == key:
            path = self.path

            if '?' in path:
                tmp = (path.split('?'))[1]
                qs = urlparse.parse_qs(tmp, keep_blank_values=True)

            if qs.has_key('command'):
                cmd = qs.pop('command')[0]
            if (qs.has_key('system')):
                system = qs.pop('system')[0]
            if (qs.has_key('param')):
                param = qs.pop('param')[0]

            res_body['command'] = cmd
            res_body['system'] = system
            res_body['param'] = param

            # must have exception handling
            ret = func_map[cmd](system, param)

            res_body['result'] = ret

            self.do_HEAD()
            self.wfile.write(res_body)

            BaseHTTPRequestHandler.do_GET(self)
        else:
            self.do_AUTHHEAD()
            self.wfile.write(self.headers.getheader('Authorization'))
            self.wfile.write('not authenticated')

def run(handlerclass=HTTPServer, handler_class=RestHandler, port=8000):
    server_address = ("", port)
    httpd = handlerclass(server_address, handler_class)
    httpd.serve_forever()


def rest_server_start():
    rest_server_daemon = multiprocess.Process(name='rest_server', target=run)
    rest_server_daemon.daemon = True
    rest_server_daemon.start()
