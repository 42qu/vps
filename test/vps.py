#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import _env
from ops.vps import XenVPS
import unittest
import conf

class TestVPS (unittest.TestCase):
    
    def test_vps (self):
        pass
        vps = XenVPS (1)
        self.assertEqual (vps.name, "vps01")
        if conf.USE_LVM:
            self.assertEqual(vps.root_store.dev, "/dev/%s/vps01_root" % (conf.VPS_LVM_VGNAME))
            self.assertEqual(vps.swap_store.dev, "/dev/%s/vps01_swap" % (conf.VPS_LVM_VGNAME))
        else:
            self.assertEqual (vps.root_store.filepath, "/vps/vps01.img")
            self.assertEqual (vps.root_store.filepath, "/swp/vps01.swp")
        self.assertEqual (vps.config_path, "/etc/xen/vps01")
        self.assertEqual (vps.auto_config_path, "/etc/xen/auto/vps01")
#        self.assertEqual (vps.xen_bridge, "br0")

if "__main__" == __name__:
    unittest.main()

