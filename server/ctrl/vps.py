#coding:utf-8
import _env
from saas.ttypes import Cmd, Vps
from server.model.vps import task_by_host_id, task_done
from model.vps_sell import VpsOne
import logging

class Handler(object):
    def todo(self, host_id, cmd):
        r = task_by_host_id(host_id, cmd)
        #print "todo",host_id , cmd , r
        return r 


    def done(self, host_id, cmd, id, state, message):
        task_done(host_id, cmd, id, state, message)

    def netflow_save(self, host_id, netflow, timestamp):
        print host_id , netflow, timestamp

    def vps(self, vps_id):
        try:
            vps = VpsOne.mc_get(vps_id)
            if not vps:
                return Vps()
            
            ip = vps.ip_autobind() # what if no ip can be autobind ?
            if ip:
                ipv4         = ip.ip
                ipv4_netmask = ip.netmask
                ipv4_gateway = ip.gateway
            else:
                ipv4 = ipv4_netmask = ipv4_gateway = 0

            return Vps(
                id=vps.id,

                ipv4=ipv4,
                ipv4_netmask=ipv4_netmask,
                ipv4_gateway=ipv4_gateway,

                password=vps.password,
                os=vps.os,
                hd=vps.hd,
                ram=vps.ram,

                cpu     = vps.cpu,
                host_id = 2, #TODO
                state   = vps.state,
                ipv4_inter = vps.ip_inter
            )
        except Exception, e:
            logging.exception (e)
            return Vps ()

if __name__ == '__main__':
    pass

    vps = VpsOne.mc_get(2)
    print dir (vps)
    print vps.ip_inter_str, vps.ip_list
    #handler = Handler()
    #print handler.vps(40)
#    from zkit.ip import int2ip
#    print int2ip(-16)
