#coding:utf-8
import _env
import sys
from model._db import redis
from saas.ttypes import  Cmd
from array import array
from model.vps_sell import vps_one_list_by_vps_order, VpsOrder, VPS_STATE_PAY
from model.mail import mq_sendmail  


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

def vps_saas_cmd_reboot(host_id, id):
    return _vps_saas_cmd_new(Cmd.REBOOT, host_id, id)

def vps_saas_cmd_open(host_id, id):
    return _vps_saas_cmd_new(Cmd.OPEN, host_id, id)

def task_done(host_id, cmd, id, state, message):
    if cmd:
        if redis.lrem(REDIS_VPS_SAAS_CMD%(host_id, cmd), id):
            pass
            #TODO 删除存在的

    mq_sendmail(
        "task_done(host_id=%s, cmd=%s, id=%s, state=%s, message=%s)"%(
            host_id, Cmd._VALUES_TO_NAMES.get(cmd,"?"), id, state, message
        ),
        "",
        "42qu-vps-saas@googlegroups.com"
    )

if __name__ == '__main__':
#    task = task_by_host_id(2)
#    print task_done(2, task)
#    print task
    #from time import time
    task_done(1,2,1,0,"")
