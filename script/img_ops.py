#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from misc import _call_cmd
import tempfile
import subprocess
import time
import re
import os


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

    _call_cmd ("losetup -f %s" % (img_path))
    lo_dev = check_loop (img_path)
    assert lo_dev
    return lo_dev

def teardown_loop (lo_dev):
    _call_cmd ("losetup -d %s" % (lo_dev))

def mount_loop (img_path):
    """ create temporary mount point and mount loop file """
    tmp_mount = tempfile.mkdtemp (prefix='mountpoint')
    lo_dev = setup_loop (img_path)
    _call_cmd ("mount %s %s" % (lo_dev, tmp_mount))
    return (lo_dev, tmp_mount)

def umount_loop (lo_dev, tmp_mount):
    """ umount loop file and delete temporary mount point """
    _call_cmd ("umount %s" % (tmp_mount))
    teardown_loop (lo_dev)
    os.rmdir (tmp_mount)

