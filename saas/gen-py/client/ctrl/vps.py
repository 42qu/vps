#coding:utf-8

from config import HOST_ID
from saas.ttypes import Action
from _route import route 
from _handler import Handler

@route(Action.OPEN)
def _open(client, id):
    print "open", id

@route(Action.CLOSE)
def _close(client, id):
    print "close", id

@route(Action.RESTART)
def _restart(client, id):
    print "restart", id


handler = Handler(route, HOST_ID)
