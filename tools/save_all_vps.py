#!/usr/bin/env python
# coding:utf-8

import getopt
import os
import _env
import conf
import sys
import multiprocessing
from vps_mgr import VPSMgr
from ops.vps import XenVPS
from ops.ixen import XenStore, get_xen_inf
import ops.vps_common as vps_common

def save (name):
    xen = get_xen_inf ()
    client = VPSMgr ()
    save_file = os.path.join (conf.SAVE_PATH, name)
    xen.save (name, save_file)
    client.logger.info ("saved %s to %s" % (name, save_file))
    


def save_all (proc_num):
    assert os.path.isdir (conf.SAVE_PATH)
    domain_dict = XenStore.domain_name_id_map ()
    del domain_dict['Domain-0']
    names = domain_dict.keys ()
    pool = multiprocessing.Pool(proc_num)
    pool.map (save, names)
     

def usage ():
    print "%s parallel_proccess_number" % (sys.argv[0])


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        usage ()
        os._exit (0)
    optlist, args = getopt.gnu_getopt (sys.argv[1:], "", [
                 "help", 
                 ])
    for opt, v in optlist:
        if opt == '--help': 
            usage ()
            os._exit (0)
    proc_num = int (args[0])
    if proc_num <= 1:
        print >> sys.stderr, "proc_num cannot smaller than 2"
        os._exit (1)

    save_all (proc_num)


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
