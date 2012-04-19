#coding:utf-8
import _env
import sys
from model._db import redis
from saas.ttypes import  Task , Cmd
from array import array
from model.vps_sell import vps_one_list_by_vps_order, VpsOrder, VPS_STATE_PAY

REDIS_VPS_SAAS_CMD = 'VpsSaasCmd:%s'         
REDIS_VPS_SAAS_CMD_META = "VpsSaasCmdIn:%s"

def task_dumps(cmd, id):
    s = array('I')
    s.append(cmd)
    s.append(id)
    return s.tostring()

def _vps_saas_cmd_new(cmd , host_id , id, key=REDIS_VPS_SAAS_CMD):
    if not cmd:
        return
    r = task_dumps(cmd, id)
    key = key%host_id
    p = redis.pipeline()
    p.lrem(key, r)
    p.rpush(key, r)
    p.execute()

def task_loads(t):
    s = array('I')
    s.fromstring(t)
    return Task(*s)

def _task_meta(task , host_id):
    cmd = task.cmd
    id = task.id
    if cmd == Cmd.OPEN:
        order = VpsOrder.get(id)
        if order:
            for i in vps_one_list_by_vps_order(order):
                if i.state == VPS_STATE_PAY:
                    _vps_saas_cmd_new(cmd, host_id, i.id) 

def task_by_host_id(host_id):
    while True:
        t = redis.lpop(REDIS_VPS_SAAS_CMD_META%host_id)
        if not t:
            break
        task = task_loads(t)
        _task_meta(task, host_id)

    key = REDIS_VPS_SAAS_CMD%host_id
    t = redis.rpoplpush(key , key)
    if t:
        return task_loads(t)
    return Task()

def vps_saas_cmd_open(host_id, id):
    return _vps_saas_cmd_new(Cmd.OPEN, host_id, id, REDIS_VPS_SAAS_CMD_META)

def task_done(host_id, task):
    if not task.cmd:
        return
    s = task_dumps(task.cmd, task.id)
    redis.lrem(REDIS_VPS_SAAS_CMD%host_id, s)

if __name__ == '__main__':
    task = task_by_host_id(2)
    print task_done(2, task)
    print task
