#coding:utf-8

from conf import HOST_ID
from saas.ttypes import Cmd
from _route import route 
from _handler import Handler




@route(Cmd.OPEN)
def _open(client, id):
    print client.vps(id)

@route(Cmd.CLOSE)
def _close(client, id):
    print "close", id

@route(Cmd.RESTART)
def _restart(client, id):
    print "restart", id


handler = Handler(route, HOST_ID)
