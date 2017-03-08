# Copyright (c) 2017 by Telcoware kimjt
# All Rights Reserved.
# SONA Monitoring Solutions.

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import base64
import multiprocessing as multiprocess

key = base64.b64encode("admin:admin")


class RestHandler(BaseHTTPRequestHandler):
    ''' Main class to present webpages and authentication. '''
    def do_HEAD(self):
        print "send header"
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_AUTHHEAD(self):
        print "send header"
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Test\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        global key
        ''' Present frontpage with user authentication. '''
        if self.headers.getheader('Authorization') == None:
            self.do_AUTHHEAD()
            self.wfile.write('no auth header received')
            pass
        elif self.headers.getheader('Authorization') == 'Basic '+key:
            BaseHTTPRequestHandler.do_GET(self)
            pass
        else:
            self.do_AUTHHEAD()
            self.wfile.write(self.headers.getheader('Authorization'))
            self.wfile.write('not authenticated')
            pass


def run(handlerclass=HTTPServer, handler_class=RestHandler, port=8000):
    server_address = ("", port)
    httpd = handlerclass(server_address, handler_class)
    httpd.serve_forever()


# def rest_server_start(self):
#     rest_server_daemon = multiprocess.Process(name='rest_server', target=run)
#     rest_server_daemon.daemon = True
#     rest_server_daemon.start()
