#coding:utf-8
import _env
from saas.ttypes import Cmd, Task, Vps
from server.model.vps import task_by_host_id, task_done
from model.vps_sell import VpsOne

class Handler(object):
    def todo(self, host_id, cmd):
        return task_by_host_id(host_id, cmd)


    def done(self, host_id, todo, state, message):
        task_done(host_id, task, state, message)

    def vps(self, vps_id):
        vps = VpsOne.mc_get(vps_id)
        if not vps:
            return Vps()

        ip = vps.ip_autobind()

        return Vps(
            id=vps.id,
            ipv4=ip.ip,
            ipv4_netmask=ip.netmask,
            ipv4_gateway=ip.gateway,
            password=vps.password,
            os=vps.os,
            hd=vps.hd,
            ram=vps.ram,
            cpu=vps.cpu,
            host_id=2, #TODO
            #host_id = vps.host_id
        )

if __name__ == '__main__':
    pass
    handler = Handler()
    print handler.vps(28)
    from zkit.ip import int2ip
    print int2ip(-16)
