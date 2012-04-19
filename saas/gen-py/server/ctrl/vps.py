#coding:utf-8
import _env
from saas.ttypes import Cmd, Task
from server.model.vps import task_by_host_id, task_done 

class Handler(object):
    def todo(self, host_id):
        return task_by_host_id(host_id)
 
    def vps(self, vps_id):
        pass

    def done(self, task):
        task_done(task)

if __name__ == "__main__":
    pass
    print handler.done(2)
