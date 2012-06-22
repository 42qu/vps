#coding:utf-8
import _env
import sys
from model._db import redis
from saas.ttypes import  Cmd
from array import array
from model.vps_sell import vps_one_list_by_vps_order, VpsOrder, VPS_STATE_PAY
from model.mail import mq_sendmail
from time import time


REDIS_VPS_SAAS_CMD = 'VpsSaasCmd:%s.%s'


def _vps_saas_cmd_new(cmd , host_id , id):
    if not cmd:
        return
    key = REDIS_VPS_SAAS_CMD%(host_id, cmd)
    p = redis.pipeline()

    if cmd == Cmd.REBOOT:
        p.zadd(key, id, time())
    else:
        p.lrem(key, id)
        p.rpush(key, id)

    p.execute()


def task_by_host_id(host_id, cmd):
    key = REDIS_VPS_SAAS_CMD%(host_id, cmd)
    #print cmd == Cmd.REBOOT
    if cmd == Cmd.REBOOT:
        now = time()
        redis.zremrangebyscore(key, 0 , now-600) #存活期 10 分钟
        t = redis.zrange(key, 0, 0)
        if t:
            t = t[0]
            redis.zadd(key, t, now)
            return int(t)
    else:
        t = redis.rpoplpush(key , key)
        #print "t", t
        if t:
            return int(t)
    #print "cmd", ".............."
    return 0

def vps_saas_cmd_os(host_id, id):
    if host_id:
        return _vps_saas_cmd_new(Cmd.OS, host_id, id)

def vps_saas_cmd_reboot(host_id, id):
    if host_id:
        return _vps_saas_cmd_new(Cmd.REBOOT, host_id, id)

def vps_saas_cmd_close(host_id, id):
    if host_id:
        return _vps_saas_cmd_new(Cmd.CLOSE, host_id, id)

def vps_saas_cmd_open(host_id, id):
    if host_id:
        return _vps_saas_cmd_new(Cmd.OPEN, host_id, id)

def task_done(host_id, cmd, id, state, message):
    if cmd:
        key = REDIS_VPS_SAAS_CMD%(host_id, cmd)
        if cmd == Cmd.REBOOT:
            rem = redis.zrem
        else:
            rem = redis.lrem

        count = rem(key, id)
    else:
        count = 0

    mq_sendmail(
        'task_done(host_id=%s, cmd=%s, id=%s, state=%s, message=%s) rem count = %s'%(
            host_id, Cmd._VALUES_TO_NAMES.get(cmd, '?'), id, state, message, count
        ),
        '',
        '42qu-vps-saas@googlegroups.com'
    )

    if cmd == Cmd.OPEN:
        from model.vps_sell import vps_order_open_by_vps_id
        if state == 0:
            vps_order_open_by_vps_id(id)
            
    return count

if __name__ == '__main__':
#    task = task_by_host_id(2)
#    print task_done(2, task)
#    print task
    #from time import time
    #task_done(1,Cmd.OPEN, 36,0,"")
    #vps_saas_cmd_reboot(3, 95)
    pass
    
    
    
