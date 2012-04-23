#coding:utf-8
import _env
import sys
from model._db import redis
from saas.ttypes import  Cmd
from array import array
from model.vps_sell import vps_one_list_by_vps_order, VpsOrder, VPS_STATE_PAY

REDIS_VPS_SAAS_CMD = 'VpsSaasCmd:%s.%s'


def _vps_saas_cmd_new(cmd , host_id , id):
    if not cmd:
        return
    key = REDIS_VPS_SAAS_CMD%(host_id, cmd)
    p = redis.pipeline()
    p.lrem(key, id)
    p.rpush(key, id)
    p.execute()


def task_by_host_id(host_id, cmd):
    key = REDIS_VPS_SAAS_CMD%(host_id, cmd)
    t = redis.rpoplpush(key , key)
    if t:
        return int(t)
    return 0 

def vps_saas_cmd_open(host_id, id):
    return _vps_saas_cmd_new(Cmd.OPEN, host_id, id)

def task_done(host_id, task, state, message):
    cmd = task.cmd
    if not cmd:
        return
    s = task_dumps(cmd, task.id)
    redis.lrem(REDIS_VPS_SAAS_CMD%(host_id, cmd), s)

if __name__ == '__main__':
    task = task_by_host_id(2)
    print task_done(2, task)
    print task

