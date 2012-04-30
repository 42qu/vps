#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import _env
import os
import re
from lib.command import call_cmd, search_path, Command, CommandException

def get_xen_inf ():
    if XenXM.available():
        return XenXM ()
    elif XenXL.available ():
        return XenXL ()
    else:
        raise Exception ("xm-tools not available")

class IXen (object):

    @staticmethod
    def available ():
        raise NotImplementedError ()

    @classmethod
    def is_running (cls, domain):
        return cls.uptime (domain) and True or False

    @staticmethod
    def create (xen_config):
        raise NotImplementedError ()

    @staticmethod
    def reboot (domain):
        raise NotImplementedError ()

    @staticmethod
    def shutdown (domain):
        raise NotImplementedError ()

    @staticmethod
    def uptime (domain):
        raise NotImplementedError ()

    @staticmethod
    def mem_free ():
        """ return mem free (MB) in Xen """
        raise NotImplementedError ()


class XenXM (IXen):

    @staticmethod
    def available ():
        path = search_path ("xm")
        return path and True or False

    @staticmethod
    def create (xen_config):
        if not os.path.exists (xen_config):
            raise Exception ("%s not exist" % (xen_config))
        call_cmd ("xm create %s" % (xen_config))

    @staticmethod
    def reboot (domain):
        call_cmd ("xm reboot %s" % (domain))

    @staticmethod
    def shutdown (domain):
        call_cmd ("xm shutdown %s" % (domain))

    @staticmethod
    def mem_free ():
        """ return mem free (MB) in Xen """
        out = call_cmd ("xm info | grep free_memory")
        return int(out.strip("\r\n").split (":")[1].strip ())

    @staticmethod
    def uptime (domain):
        cmd = "xm uptime %s | grep %s " % (domain, domain)
        c = Command (cmd)
        status, out = c.read_from ()
        if status == 0:
            return out.split ()[2]
        elif re.match (r"^.*Domain '.+?' does not exist.*$", out):
            return None
        else:
            raise CommandException (cmd, msg=out, status=status)


class XenXL (IXen):

    @staticmethod
    def available ():
        path = search_path ("xl")
        return path and True or False

    @staticmethod
    def create (xen_config):
        if not os.path.exists (xen_config):
            raise Exception ("%s not exist" % (xen_config))
        call_cmd ("xl create %s" % (xen_config))

    @staticmethod
    def reboot (domain):
        call_cmd ("xl reboot %s" % (domain))

    @staticmethod
    def shutdown (domain):
        call_cmd ("xl shutdown %s" % (domain))

    @staticmethod
    def mem_free ():
        """ return mem free (MB) in Xen """
        out = call_cmd ("xl info | grep free_memory")
        return int(out.strip("\r\n").split (":")[1].strip ())

    @staticmethod
    def uptime (domain):
        cmd = "xl uptime %s | grep %s " % (domain, domain)
        c = Command (cmd)
        status, out = c.read_from ()
        if status == 0:
            return out.split ()[2]
        elif re.match (r"^.*Domain '.+?' does not exist.*$", out):
            return None
        else:
            raise CommandException (cmd, msg=out, status=status)
            

if __name__ == '__main__':
    import unittest
    class TestXenInf (unittest.TestCase):

        def setUp (self):
            self.xeninf = get_xen_inf ()
            print "testing %s" % (self.xeninf.__class__.__name__)

        def test_uptime (self):
            self.assertEqual (self.xeninf.uptime ("nonexistvps"), None)

    
    unittest.main ()

