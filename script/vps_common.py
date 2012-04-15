#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import random
import string
import os
import tempfile
import time
import re

def call_cmd (cmd):
    res = os.system (cmd)
    if res != 0:
        raise Exception ("%s exit with %d" % (cmd, res))

def gen_password (length=10):
    return "".join ([ random.choice(string.hexdigits) for i in xrange (0, length) ])

def check_loop (img_path):
    "return loop device name matching img_path. return None when not found"
    _out = subprocess.check_output (["losetup", "-a"])
    lines = _out.split ("\n")
    time.sleep (1)
    for line in lines:
        if line.find (img_path) != -1:
            om = re.match (r"^(/dev/loop\d+):.*$", line)
            if om:
                return om.group (1)
    return None


def setup_loop (img_path):
    """ return loop device filename """
    img_path = os.path.abspath (img_path)
    lo_dev = check_loop (img_path)
    if lo_dev:
        raise Exception ("img has already been mounted as %s" % (lo_dev))

    call_cmd ("losetup -f %s" % (img_path))
    lo_dev = check_loop (img_path)
    assert lo_dev
    return lo_dev

def teardown_loop (lo_dev):
    call_cmd ("losetup -d %s" % (lo_dev))


def mount_loop_tmp (img_path, readonly=False):
    """ create temporary mount point and mount loop file """
    tmp_mount = tempfile.mkdtemp (prefix='mountpoint')
    if readonly:
        call_cmd ("mount %s %s -o loop,ro" % (img_path, tmp_mount))
    else:
        call_cmd ("mount %s %s -o loop" % (img_path, tmp_mount))
    return tmp_mount

def umount_tmp (tmp_mount):
    """ umount loop file and delete temporary mount point """
    call_cmd ("umount %s" % (tmp_mount))
    os.rmdir (tmp_mount)

