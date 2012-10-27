#!/usr/bin/env python
# coding:utf-8

import sys
import _env
import ops.migrate as migrate
import conf
from lib.log import Log
from lib.command import call_cmd
import unittest
import threading
import conf
import os


class TestSendfile (unittest.TestCase):

    def test_1 (self):
        logger =  Log ("test", config=conf)
        migsvr = migrate.MigrateServer (logger)
        migsvr.start ()
        def foo ():
            migsvr.loop ()
            return
        th = threading.Thread (target=foo)
        th.setDaemon (1)
        th.start ()

        client = migrate.MigrateClient (logger, "127.0.0.1")
        call_cmd ("dd if=/proc/interrupts of=/tmp/test")
        client.sendfile ("/tmp/test", "/tmp/test1")
        migsvr.stop ()


if __name__ == '__main__':
    unittest.main ()
    time.sleep (2)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
