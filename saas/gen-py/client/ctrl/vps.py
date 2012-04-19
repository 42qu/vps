#coding:utf-8

import _env
from conf import HOST_ID
from saas.ttypes import Cmd
from _route import route
from _handler import Handler



def vps_open(vps):
    print vps

@route(Cmd.OPEN)
def _open(client, id):
    vps = client.vps(id)
    vps_open(vps)

@route(Cmd.CLOSE)
def _close(client, id):
    print 'close', id

@route(Cmd.RESTART)
def _restart(client, id):
    print 'restart', id


handler = Handler(route, HOST_ID)

if '__main__' == __name__:
    from saas.ttypes import Vps
    vps = Vps(ipv4_gateway=2013143905, ram=2048, cpu=1, ipv4_netmask=-16, host_id=2, password='k5chpa2n4mz2', os=21, id=28, hd=50, ipv4=2013143908)
    vps_open(vps)

