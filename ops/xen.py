#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import _env
import os
from lib.command import call_cmd, search_path, Command

class IXen (object):

    @staticmethod
    def available ():
        raise NotImplementedError ()

    @classmethod
    def is_running (cls, domain):
        raise NotImplementedError ()

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

    @classmethod
    def is_running (cls, domain):
        return cls.uptime (domain)

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
        c = Command ("xm info | grep free_memory")
        status, out = c.read_from ()
        out = out.strip ("\r\n")
        if status == 0:
            return int(out.split (":")[1].strip ())

    @staticmethod
    def uptime (domain):
        c = Command ("xm uptime %s | grep %s " % (domain, domain))
        status, out = c.read_from ()
        out = out.strip ("\r\n")
        if status == 0:
            return out.split ("")[2]
        return None



class XenXL (IXen):

    @staticmethod
    def available ():
        path = search_path ("xl")
        return path and True or False

    @classmethod
    def is_running (cls, domain):
        return cls.uptime (domain)


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
        c = Command ("xl info | grep free_memory")
        status, out = c.read_from ()
        out = out.strip ("\r\n")
        if status == 0:
            return int(out.split (":")[1].strip ())



    @staticmethod
    def uptime (domain):
        c = Command ("xl uptime %s | grep %s " % (domain, domain))
        status, out = c.read_from ()
        try:
            if status == 0:
                return out.split ("")[2]
        except IndexError:
            return None
        return None



