#!/usr/bin/env python

import _env
from vps import XenVPS
import conf
assert conf.VPS_METADATA_DIR

class VPSMetaData (object):

    def __init__ (self):
        pass

    def _filepath (xenvps):
        return 


    def load (self, vps_id)
        xv = XenVPS (vps_id)
        #TODO 
        return xv

    def save (self, xenvps):
        assert isinstance (xenvps, XenVPS)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
