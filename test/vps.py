#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import _env
from ops.vps import XenVPS
import unittest

class TestVPS (unittest.TestCase):
    
    def test_vps (self):
        pass
        vps = XenVPS (1)
        self.assertEqual (vps.name, "vps1")
        self.assertEqual (vps.img_path, "/vps/vps1.img")
        self.assertEqual (vps.swp_path, "/swp/vps1.swp")
        self.assertEqual (vps.config_path, "/etc/xen/vps1")
        self.assertEqual (vps.auto_config_path, "/etc/xen/auto/vps1")
#        self.assertEqual (vps.xen_bridge, "br0")

if "__main__" == __name__:
    unittest.main()

