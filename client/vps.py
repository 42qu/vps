#!/usr/bin/env python
#coding:utf-8
import _env

from conf import HOST_ID

from zthrift.client import run_client
from saas.ttypes import Cmd

class Route(object):
    def __init__(self):
        self._ROUTE = {}

    def __call__(self, id):
        def _(func):
            self._ROUTE[id] = func
            return func
        return _

    def get(self, id):
        return self._ROUTE.get(id, None) 


class Handler(object):
    def __init__(self, route, host_id):
        self.route = route
        self.host_id = host_id

    def __call__(self, client):
        route = self.route
        host_id = self.host_id
        task = client.todo(host_id)
        cmd = task.cmd
        if cmd:
            func = route.get(cmd)
            if func:
                func(client, task.id)
                client.done(host_id, task)



def main():

    route = Route()

    @route(Cmd.OPEN)
    def _open(saas, id):
        vps = saas.vps(id)
        #TODO
        return

    #@route(Cmd.CLOSE)
    #def _close(saas, id):
    #    print 'close', id
    #
    #@route(Cmd.RESTART)
    #def _restart(saas, id):
    #    print 'restart', id


    handler = Handler(route, HOST_ID)
    run_client(VPS, handler)
    print 'done'

if __name__ == "__main__":
    main()

