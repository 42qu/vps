#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import random
import string
import os
import tempfile
import time
import re

from command import call_cmd

#def call_cmd (cmd):
#    res = os.system (cmd)
#    if res != 0:
#        raise Exception ("%s exit with %d" % (cmd, res))

def gen_password (length=10):
    return "".join ([ random.choice(string.hexdigits) for i in xrange (0, length) ])

def gen_mac ():
    cmd = """(date; cat /proc/interrupts) | md5sum | sed -r 's/^(.{6}).*$/\\1/; s/([0-9a-f]{2})/\\1:/g; s/:$//;'"""
    s = "00:16:3e:"
    out = call_cmd (cmd)
    return s + out

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

def create_raw_image (path, size_g, mkfs_cmd):
    assert size_g > 0
    size_m = int (size_g * 1024)
    call_cmd ("dd if=/dev/zero of=%s bs=1M count=%d" % (path, size_m))
    call_cmd ("%s %s" % (mkfs_cmd, path))


def sync_img (vpsmountpoint, template_img_path):
    if vpsmountpoint[-1] != '/':
        vpsmountpoint += "/"
    template_mount = mount_loop_tmp (template_img_path, readonly=True)
    if template_mount[-1] != '/':
        template_mount += "/"
    call_cmd ("rsync -a '%s' '%s'" % (template_mount, vpsmountpoint)) 
    umount_tmp (template_mount)

def unpack_tarball (vpsmountpoint, tarball_path):
    pwd = os.getcwd()
    os.chdir (vpsmountpoint)
    try:
        if re.match ("^.*\.(tar\.gz|tgz)$", tarball_path):
            call_cmd ("tar zxf '%s'" % (tarball_path))
        elif re.match ('^.*\.(tar\.bz2|tbz2)$', tarball_path):
            call_cmd ("tar jxf '%s'" % (tarball_path))



#def check_loop (img_path):
#    "return loop device name matching img_path. return None when not found"
#    _out = subprocess.check_output (["losetup", "-a"])
#    lines = _out.split ("\n")
#    time.sleep (1)
#    for line in lines:
#        if line.find (img_path) != -1:
#            om = re.match (r"^(/dev/loop\d+):.*$", line)
#            if om:
#                return om.group (1)
#    return None
#
#
#def setup_loop (img_path):
#    """ return loop device filename """
#    img_path = os.path.abspath (img_path)
#    lo_dev = check_loop (img_path)
#    if lo_dev:
#        raise Exception ("img has already been mounted as %s" % (lo_dev))
#
#    call_cmd ("losetup -f %s" % (img_path))
#    lo_dev = check_loop (img_path)
#    assert lo_dev
#    return lo_dev
#
#def teardown_loop (lo_dev):
#    call_cmd ("losetup -d %s" % (lo_dev))



