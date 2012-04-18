#coding:utf-8

from saas.ttypes import Action
from time import sleep
from config import HOST_ID

_ROUTE = {}
def route(id):
    def _(func):
        _ROUTE[id] = func
        return func
    return _


@route(Action.OPEN)
def _open(client, id):
    print "open", id

@route(Action.CLOSE)
def _close(client, id):
    print "close", id

@route(Action.RESTART)
def _restart(client, id):
    print "restart", id



def handler(client):
    while True:
        todo = client.todo(HOST_ID)
        action = todo.action
        if action:
            func = ACTION.get(todo.action, 0)
            if func:
                func(client, todo.id)
        sleep(10)


if __name__ == "__main__":
    pass

