#coding:utf-8

from saas.ttypes import Action
from time import sleep
from config import HOST_ID

ACTION = {}
def action(id):
    def _(func):
        ACTION[id] = func
        return func
    return _


@action(Action.OPEN)
def _open(client, id):
    print id

@action(Action.CLOSE)
def _close(client, id):
    print id

@action(Action.RESTART)
def _close(client, id):
    print id



def handler(client):
    while True:
        todo = client.todo(HOST_ID)
        action = todo.action
        if action:
            func = ACTION.get(todo.action, 0)
            if func:
                func(client, id)
        sleep(10)


if __name__ == "__main__":
    pass

