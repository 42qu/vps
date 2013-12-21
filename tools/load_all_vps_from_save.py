#!/usr/bin/env python
# coding:utf-8


import glob

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


def _load(file_path):
    xen = get_xen_inf()
    client = VPSMgr()
    xen.restore(file_path)
    client.logger.info("restore %s" % (file_path))


def load_all(proc_num):
    assert os.path.isdir(conf.SAVE_PATH)
    files = glob.glob(os.path.join(conf.SAVE_PATH, '*'))
    pool = multiprocessing.Pool(proc_num)
    for file_ in files:
        pool.map(_load, file_)


def usage():
    print "%s parallel_proccess_number" % (sys.argv[0])


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        usage()
        os._exit(0)
    optlist, args = getopt.gnu_getopt(sys.argv[1:], "", [
        "help",
    ])
    for opt, v in optlist:
        if opt == '--help':
            usage()
            os._exit(0)
    proc_num = int(args[0])
    if proc_num <= 1:
        print >> sys.stderr, "proc_num cannot smaller than 2"
        os._exit(1)

    load_all(proc_num)



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
