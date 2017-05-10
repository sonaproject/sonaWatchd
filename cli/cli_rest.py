import json
import base64
import multiprocessing as multiprocess

from log_lib import LOG
from cli import CLI
from config import CONFIG
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

class RestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global global_evt

        request_sz = int(self.headers["Content-length"])
        request_str = self.rfile.read(request_sz)
        request_obj = json.loads(request_str)

        LOG.debug_log('[REST-SERVER] CLIENT INFO = ' + str(self.client_address))
        LOG.debug_log('[REST-SERVER] RECV BODY = \n' + json.dumps(request_obj, sort_keys=True, indent=4))

        if self.headers.getheader('Authorization') is None:
            LOG.debug_log('[REST-SERVER] no auth header received')

        elif not self.path.startswith('/event'):
            LOG.debug_log('[REST-SERVER] ' + self.path + ' not found')

        elif self.auth_pw(self.headers.getheader('Authorization')):
            global_evt.set()
            # add event
        else:
            LOG.debug_log('[REST-SERVER] not authenticated')

    def auth_pw(self, cli_pw):
        if cli_pw == base64.b64encode(CLI.get_auth()):
            return True

        return False

global_evt = None

def run(evt):
    global global_evt
    LOG.debug_log("--- REST Server Start --- ")

    global_evt = evt

    try:
        server_address = ("", CONFIG.get_rest_port())
        httpd = HTTPServer(server_address, RestHandler)
        httpd.serve_forever()
    except:
        LOG.exception_err_write()
        # occure rest server err event


def rest_server_start(evt):
    LOG.debug_log("--- REST Server Start --- ")

    rest_server_daemon = multiprocess.Process(name='cli_rest_svr', target=run, args=(evt,))
    rest_server_daemon.daemon = True
    rest_server_daemon.start()
