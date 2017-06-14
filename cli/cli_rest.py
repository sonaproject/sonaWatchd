import json
import base64
import os
import multiprocessing as multiprocess

from log_lib import LOG
from cli import CLI
from config import CONFIG
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

class RestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global global_evt
        global global_conn_evt
        global global_history_log

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
            global_history_log.write_history('[%s][%s][%s] %s', request_obj['system'], request_obj['item'], request_obj['grade'], request_obj['desc'])

            if request_obj['system'] == 'sonawatcher' and request_obj['item'] == 'SONAWATCHER_DISCONNECT':
                global_conn_evt.set()
                LOG.debug_log('[REST-SERVER] ' + request_obj['desc'])
            else:
                global_evt.set()
        else:
            LOG.debug_log('[REST-SERVER] not authenticated')

    def auth_pw(self, cli_pw):
        if cli_pw == base64.b64encode(CLI.get_auth()):
            return True

        return False


global_evt = None
global_conn_evt = None
global_history_log = None

def run(evt, conn_evt, rest_evt, history_log):
    global global_history_log
    global global_conn_evt
    global global_evt

    global_history_log = history_log
    global_evt = evt
    global_conn_evt = conn_evt

    LOG.debug_log("--- REST Server Start --- ")
    global_history_log.write_history("--- Event History Start ---")

    try:
        server_address = ("", CONFIG.get_rest_port())
        httpd = HTTPServer(server_address, RestHandler)
        httpd.serve_forever()

    except:
        LOG.exception_err_write()
        # occure rest server err event
        rest_evt.set()

def rest_server_start(evt, conn_evt, rest_evt, history_log):
    rest_server_daemon = multiprocess.Process(name='cli_rest_svr', target=run, args=(evt, conn_evt, rest_evt, history_log))
    rest_server_daemon.daemon = True
    rest_server_daemon.start()

    return rest_server_daemon.pid



