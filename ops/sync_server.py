#!/usr/bin/env python

import os
import socket
import ssl
import subprocess
from lib.command import Command, search_path

import time
import signal
try: 
    import json
except ImportError:
    import simplejson as json


import ops.vps_common as vps_common
import ops._env
from lib.job_queue import JobQueue, Job
from lib.rpc_server import AES_RPC_Server
import lib.io_poll as io_poll
from lib.net_io import NetHead
import conf
assert conf.RSYNC_CONF_PATH
assert conf.RSYNC_PORT
assert conf.MOUNT_POINT_DIR


            
RSYNC_SERVER_NAME = "sync_server"


class SyncServerBase(object):


    def __init__(self, logger, client_keys):
        self.logger = logger
        self.host_id = conf.HOST_ID
        self._rsync_popen = None
        self.is_running = False
        self.listen_ip = "0.0.0.0"
        self.inf_addr = (self.listen_ip, conf.INF_PORT)
        self.rsync_port = conf.RSYNC_PORT
        self.server = AES_RPC_Server(
                self.inf_addr,
                client_keys=client_keys,
                logger=logger,
                logger_debug=logger,
                )

    def loop(self):
        self.server.loop()


    def start(self):
        if self.is_running:
            return
        self.is_running = True
        #self.start_rsync()
        self.server.start(20)

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        self.server.stop()
        self.logger.info("server stopped")
        self.stop_rsync()

    def start_rsync(self):
        rsync_conf = """
uid=root
gid=root
use chroot=yes
og file=/dev/null
[%s]
    path=%s
    read only=no
    write only=yes
""" % (RSYNC_SERVER_NAME, conf.MOUNT_POINT_DIR)

        f = open(conf.RSYNC_CONF_PATH, "w")
        try:
            f.write(rsync_conf)
        finally:
            f.close()
        rsync_cmd = ["rsync", "--daemon", "--config=%s" % (conf.RSYNC_CONF_PATH), "--no-detach"]
        rsync_cmd.append("--address=%s" % (self.listen_ip))
        rsync_cmd.append("--port=%s" % (self.rsync_port))
        #self._rsync_popen = subprocess.Popen(rsync_cmd, stderr=subprocess.PIPE, close_fds=True)
        self._rsync_popen = Command(rsync_cmd)
        self._rsync_popen.start()
        self.logger.info("started rsync, pid=%s" % (self._rsync_popen.pid))
        time.sleep(1)

    def stop_rsync(self):
        assert self._rsync_popen is not None
        self.logger.info("stopping rsync")
        os.kill(self._rsync_popen.pid, signal.SIGTERM)
        self._rsync_popen.wait()
        self.logger.info("rsync stopped")

from lib.rpc import AES_RPC_Client, RPC_Exception

class SyncClientBase(object):

    def __init__(self, logger, server_ip):
        self.server_ip = server_ip
        self.logger = logger
        self.rpc = AES_RPC_Client(conf.KEY, logger)

    def connect(self, timeout=None):
        addr = (self.server_ip, conf.INF_PORT)
        if timeout:
            self.rpc.set_timeout(timeout)
        self.rpc.connect(addr)

    def close(self):
        self.rpc.close()


    def rsync(self, source, dest=None, speed=None, use_zip=False):
        """ speed is in Mbit/s """
        options = ("-avW", "--inplace", )
        if os.path.isdir(source):
            if source[-1] != "/":
                source += "/"
            if dest and dest[-1] != "/":
                dest += "/"
            if dest:
                options += ("--delete", )
        if not dest:
            dest = ""
        if speed:
            assert isinstance(speed, (int, float))
            options += ("--bwlimit", str(int(speed * 1000 / 8)), )
            use_zip = True
        if use_zip:
            options += ("-z", )
            
        cmd = ("rsync", ) + options + \
                (source, \
                "rsync://%s:%s/%s/%s" % (self.server_ip, conf.RSYNC_PORT, RSYNC_SERVER_NAME, dest)
                )
        print cmd
        p = subprocess.Popen(cmd, stderr=subprocess.PIPE, close_fds=True)
        retcode = p.wait()
        if retcode:
            stderr = "\n".join(p.stderr.readlines())
        else:
            stderr = None
        p.stderr.close()
        return retcode, stderr

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
