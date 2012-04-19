#coding:utf-8
import _env
from saas.ttypes import Cmd, Task

class Handler(object):
    def todo(self, host_id):
        return Task(Cmd.OPEN, 0)

    def vps(self, vps_id):
        pass

    def done(self, todo):
        print "done", todo.cmd , todo.id

if __name__ == "__main__":
    pass
    from model.vps_sell import REDIS_VPS_SAAS_CMD
    print REDIS_VPS_SAAS_CMD
