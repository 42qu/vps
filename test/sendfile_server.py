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
#        migsvr.start ()
#        def foo ():
#            migsvr.loop ()
#        th = threading.Thread (target=foo)
#        th.setDaemon (1)
#        th.start ()

        client = migrate.MigrateClient (logger, "127.0.0.1")
        call_cmd ("dd if=/proc/interrupts of=/tmp/test")
        port1 = migsvr.start_sendfile_svr ("/tmp/test1")
        self.assertEqual (len(migsvr._sendfile_svr_dict.keys ()), 1)
        self.assertEqual (conf.SENDFILE_PORT, port1)
        port2 = migsvr.start_sendfile_svr ("/tmp/test2")
        self.assertEqual (port2, port1 + 1)
        print port2
        ret, err = client.sendfile ("/tmp/test", "127.0.0.1", port2)
        print ret, err
        self.assertEqual (ret, 0)
        migsvr.stop_sendfile_svr (port2)
        port3 = migsvr.start_sendfile_svr ("/tmp/test3")
        self.assertEqual (port2, port3)
        ret, err = client.sendfile ("/tmp/test", "127.0.0.1", port3)
        self.assertEqual (ret, 0)
        migsvr.stop_sendfile_svr (port3)
        ret, err = client.sendfile ("/tmp/test", "127.0.0.1", port1)
        print ret, err
        self.assertEqual (ret, 0)
        migsvr.stop_sendfile_svr (port1)


if __name__ == '__main__':
    unittest.main ()
    time.sleep (2)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
