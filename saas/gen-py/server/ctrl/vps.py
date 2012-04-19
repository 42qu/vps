#coding:utf-8
import _env
from saas.ttypes import Cmd, Task
from server.model.vps import task_by_host_id 

class Handler(object):
    def todo(self, host_id):
        return task_by_host_id(host_id)
 
    def vps(self, vps_id):
        pass

    def done(self, todo):
        print "done", todo.cmd , todo.id

if __name__ == "__main__":
    pass
    print REDIS_VPS_SAAS_CMD
    handler = Handler()
    print handler.todo(2)
