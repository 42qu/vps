#coding:utf-8
import _env
import sys
from model._db import redis
from saas.ttypes import  Task , Cmd
from array import array

REDIS_VPS_SAAS_CMD = 'VpsSaasCmd:%s'         #等待开通的订单 , host_id -> id list

def task_dumps(cmd, id):
    s = array('I')
    s.append(cmd)
    s.append(id)
    return s.tostring()

def _vps_saas_cmd_new(cmd , host_id , id):
    r = task_dumps(cmd, id)
    key = REDIS_VPS_SAAS_CMD%host_id
    p = redis.pipeline()
    p.lrem(key, r)
    p.rpush(key, r)
    p.execute()

def task_by_host_id(host_id):
    key = REDIS_VPS_SAAS_CMD%host_id
    t = redis.rpoplpush(key , key)
    if t:
        s = array('I')
        s.fromstring(t)
        return Task(*s)
    return Task()

def vps_saas_cmd_open(host_id, id):
    return _vps_saas_cmd_new(Cmd.OPEN, host_id, id)

def task_done(task):
    s = task_dumps(task.cmd, task.id)
    return s

if __name__ == '__main__':
    print task_by_host_id(2)

