#!/usr/bin/env python2.6

import os
import re
import _env
from ops.xen import XenStore
from ops.vps import XenVPS
from ops.vps_ops import VPSOps
from vps_mgr import VPSMgr
import pprint

def gen_meta (vps_mgr, domain_dict, vps_id):
    xv = XenVPS (vps_id)
    vps = vps_mgr.query_vps (vps_id)
    if not vps_mgr.vps_is_valid (vps):
        print "no backend data for %s " % vps_id
        return
    domain_id = domain_dict[xv.name]
    vif_datas = XenStore.get_vif_by_domain_id (domain_id)
    vps_mgr.setup_vps (xv, vps)
    #xv.add_extra_storage (1, 964) #TEST
    vpsops = VPSOps (vps_mgr.logger)
    if len (vif_datas.values ()) == 1:
        vif_data = vif_datas.values()[0]
        if vif_data['online'] == '1':
            if vif_data.has_key ('vifname'):
                xv.vifs[vif_data['vifname']].mac = vif_data['mac']
            else:
                vif_id = vif_datas.items ()[0][0]
                vif_name = 'vif%s.%s' % (domain_id, vif_id)
                del xv.vifs[xv.name]
                xv.add_netinf_ext (ip=xv.ip, netmask=xv.netmask, mac=vif_data['mac'])
        #vpsops.create_xen_config (xv)
        vpsops.save_vps_meta (xv, override=True)


def main ():
    vps_mgr = VPSMgr ()
    domain_dict = XenStore.domain_name_id_map()
    for k, v in domain_dict.iteritems ():
        om = re.match (r'^vps(\d+)$', k) 
        if om:
            print int(om.group(1))
            gen_meta (vps_mgr, domain_dict, int(om.group (1)))
#    gen_meta (vps_mgr, domain_dict, 166)

if __name__ == '__main__':
    main ()


    
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
