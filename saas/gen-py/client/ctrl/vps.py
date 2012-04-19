#coding:utf-8

import _env
from conf import HOST_ID
from saas.ttypes import Cmd
from _route import route
from _handler import Handler
from client.model.vps import vps_open



@route(Cmd.OPEN)
def _open(client, id):
    vps = client.vps(id)
    print vps
    vps_open(vps)

@route(Cmd.CLOSE)
def _close(client, id):
    print 'close', id

@route(Cmd.RESTART)
def _restart(client, id):
    print 'restart', id


handler = Handler(route, HOST_ID)

if __name__ == "__main__":
    pass
