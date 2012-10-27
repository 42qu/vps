#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import _env
import os
import re
from lib.command import call_cmd, search_path, Command, CommandException


def _get_xen_inf ():
    if XenXM.available():
        return XenXM ()
    elif XenXL.available ():
        return XenXL ()
    else:
        raise Exception ("xm-tools not available")


def get_xen_inf ():
    return _xentool

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
    def save (domain, path):
        raise NotImplementedError ()

    @staticmethod
    def restore (path):
        raise NotImplementedError ()

#    @staticmethod
#    def reboot (domain):
#        raise NotImplementedError ()

    @staticmethod
    def shutdown (domain):
        raise NotImplementedError ()

    @staticmethod
    def destroy (domain):
        raise NotImplementedError ()

    @staticmethod
    def uptime (domain):
        raise NotImplementedError ()

    @staticmethod
    def mem_free ():
        """ return mem free (MB) in Xen """
        raise NotImplementedError ()

    @staticmethod
    def mem_total ():
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
    def save (domain, path):
        call_cmd ("xm save %s %s" % (domain, path))

    @staticmethod
    def restore (path):
        call_cmd ("xm restore %s" % (path))

#    @staticmethod
#    def reboot (domain):
#        # xm reboot is broken, and will cause subsequenced xm shutdown not working
#        call_cmd ("xm reboot %s" % (domain))

    @staticmethod
    def shutdown (domain):
        call_cmd ("xm shutdown %s" % (domain))

    @staticmethod
    def destroy (domain):
        call_cmd ("xm destroy %s" % (domain))


    @staticmethod
    def mem_free ():
        """ return mem free (MB) in Xen """
        out = call_cmd ("xm info | grep free_memory")
        return int(out.strip("\r\n").split (":")[1].strip ())

    @staticmethod
    def mem_total ():
        """ return mem total (MB) in Xen """
        out = call_cmd ("xm info | grep total_memory")
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

#    @staticmethod
#    def reboot (domain):
#        call_cmd ("xl reboot %s" % (domain))

    @staticmethod
    def shutdown (domain):
        call_cmd ("xl shutdown %s" % (domain))

    @staticmethod
    def destroy (domain):
        call_cmd ("xl destroy %s" % (domain))

    @staticmethod
    def mem_free ():
        """ return mem free (MB) in Xen """
        out = call_cmd ("xl info | grep free_memory")
        return int(out.strip("\r\n").split (":")[1].strip ())

    @staticmethod
    def mem_total ():
        """ return mem total (MB) in Xen """
        out = call_cmd ("xl info | grep total_memory")
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


class XenStore (object):

    @staticmethod
    def _list (path):
        out = call_cmd ("xenstore-list %s" % (path))
        return out.split ("\n")

    @staticmethod
    def _read (path):
        return call_cmd ("xenstore-read %s" % (path))

    @staticmethod
    def _get_tree (path):
        """ return a dict , parsed from xenstore-ls """
        cmd = "xenstore-ls %s" % (path)
        out = call_cmd (cmd)
        lines = out.split ("\n")
        _static = {
                'node': {},
                'last_key': None,
                'last_value': None,
                'last_space': 0,
        }
        stack = []
        def __process (space, key, value):
            #print _static['last_space'], space, _static['last_key'], _static['last_value'], key, value
            if _static['last_key'] is None:
                _static['last_space'] = 0
            elif _static['last_value'] == "" and _static['last_space'] + 1 == space:
                _static['node'][_static['last_key']] = {} 
                stack.append (_static['node'])
                _static['node'] = _static['node'][_static['last_key']]
            elif _static['last_space'] > space:
                _static['node'][_static['last_key']] = _static['last_value']
                for i in xrange (0, _static['last_space'] - space):
                    _static['node'] = stack.pop ()
            else:
                assert _static['last_space'] == space
                _static['node'][_static['last_key']] = _static['last_value']
            _static['last_key'] = key
            _static['last_value'] = value
            _static['last_space'] = space
            return
                
        reg_key_value = re.compile (r"^(\s*)([\w\-]+)\s*=\s*\"(.*)\".*$")
        for line in lines:
            om = re.match (reg_key_value, line)
            if not om:
                raise Exception ("unexpect format: %s" % (line))
            space = len (om.group (1))
            key = om.group (2)
            value = om.group (3)
            __process (space, key, value)
        __process (0, None, None)
        return _static['node']
        

    @classmethod
    def domain_name_id_map (cls):
        domain_list = cls._list ("/local/domain") 
        result_dict = {}
        for domain_id in domain_list:
            name = cls._read ("/local/domain/%s/name" % (domain_id))
            name = name.strip ("\r\n")
            result_dict[name] = int(domain_id)
        return result_dict

    @classmethod
    def get_vif_by_domain_id (cls, domain_id):
        return cls._get_tree ("/local/domain/0/backend/vif/%s" % (domain_id))
        

_xentool = _get_xen_inf ()  # check xen tools and setup

if __name__ == '__main__':
    import unittest
    class TestXenInf (unittest.TestCase):

        def setUp (self):
            self.xeninf = get_xen_inf ()
            print "testing %s" % (self.xeninf.__class__.__name__)

        def test_uptime (self):
            self.assertEqual (self.xeninf.uptime ("nonexistvps"), None)

    
    unittest.main ()

