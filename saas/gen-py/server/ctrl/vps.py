#coding:utf-8
import _env
from saas.ttypes import Cmd, Task
from model.vps_sell import REDIS_VPS_SAAS_CMD
from model._db import redis
from array import array

class Handler(object):
    def todo(self, host_id):
        key = REDIS_VPS_SAAS_CMD%host_id
        t = redis.rpoplpush(key , key)
        if t:
            s = array('I')
            s.fromstring(t)
            return Task(*s)
        return Task()

    def vps(self, vps_id):
        pass

    def done(self, todo):
        print "done", todo.cmd , todo.id

if __name__ == "__main__":
    pass
    print REDIS_VPS_SAAS_CMD
    handler = Handler()
    print handler.todo(2)
