#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import random
import string
import os
import tempfile
import time
import re
import _env
from lib.command import call_cmd, search_path

assert search_path ("file")

#def call_cmd (cmd):
#    res = os.system (cmd)
#    if res != 0:
#        raise Exception ("%s exit with %d" % (cmd, res))

def ping (ip):
    return 0 == os.system ("ping -i0.3 -c2 -W1 %s >/dev/null" % (ip))

def call_cmd_via_ssh (ip, user, password, cmd):
    import paramiko
    client = paramiko.SSHClient()
#    client.load_system_host_keys ()
    client.set_missing_host_key_policy (paramiko.AutoAddPolicy ())
    client.connect (ip, username=user, password=password, look_for_keys=False)
    try:
        stdin, stdout, stderr = client.exec_command(cmd)
        try:
            exit_status = stdout.channel.recv_exit_status()
            out = "\n".join (stdout.readlines ())
            err = "\n".join (stderr.readlines ())
            return exit_status, out, err
        finally:
            stdin.close ()
            stdout.close ()
            stderr.close ()
    finally:
        client.close ()


def gen_password (length=10):
    return "".join ([ random.choice(string.hexdigits) for i in xrange (0, length) ])

def gen_mac ():
    cmd = """(date; cat /proc/interrupts) | md5sum | sed -r 's/^(.{6}).*$/\\1/; s/([0-9a-f]{2})/\\1:/g; s/:$//;'"""
    s = "00:16:3e:"
    out = call_cmd (cmd)
    return s + out

def mkdtemp (prefix=None, temp_dir=None):
    # tempfile.mkdtemp on some system (like centos5) is buggy,  but this implement is not protected against race condition either 
    for i in xrange (0, 3):
        tmp_mount = tempfile.mkdtemp (prefix=prefix, dir=temp_dir)
        if os.path.isdir (tmp_mount):
            return tmp_mount
        time.sleep (0.2)
    raise Exception ("cannot create temporary mountpoint")
            

def mount_loop_tmp (img_path, readonly=False, temp_dir=None):
    """ create temporary mount point and mount loop file """
    tmp_mount = mkdtemp ("mpl", temp_dir=temp_dir)
    try:
        if readonly:
            call_cmd ("mount %s %s -o loop,ro,noatime" % (img_path, tmp_mount))
        else:
            call_cmd ("mount %s %s -o loop,noatime" % (img_path, tmp_mount))
    except Exception, e:
        os.rmdir (tmp_mount)
        raise e
    return tmp_mount

def mount_partition_tmp (dev_path, readonly=False, temp_dir=None):
    prefix = "mp" + os.path.basename (dev_path)
    tmp_mount = mkdtemp (prefix, temp_dir=temp_dir)
    try:
        if readonly:
            call_cmd ("mount %s %s -o ro,noatime" % (dev_path, tmp_mount))
        else:
            call_cmd ("mount %s %s -o noatime" % (dev_path, tmp_mount))
    except Exception, e:
        os.rmdir (tmp_mount)
        raise e
    return tmp_mount

def get_link_target (l):
    if os.path.islink (l):
        t = os.readlink (l)
        l = os.path.join (os.path.dirname (l), t)
        return os.path.abspath (l)
    return l

def get_blk_size (dev):
    out = call_cmd ("blockdev --getsize64 %s" % (dev))
    out = out.strip ()
    return int (out)


def get_fs_type (dev_path):
    if os.path.islink (dev_path):
        dev_path = get_link_target (dev_path)
    assert os.path.exists(dev_path)
    out = call_cmd ("file -s %s" % (dev_path))
    if re.match (r"^.*ext4.*?$", out, re.I):
        return "ext4"
    elif re.match (r"^.*ext3.*?$", out, re.I):
        return "ext3"
    elif re.match (r"^.*ext2.*?", out, re.I):
        return "ext2"
    elif re.match (r"^.*swap.*?", out, re.I):
        return "swap"
    elif re.match(r"^.*ReiserFS.*?", out, re.I):
        return "reiserfs"
    elif re.match (r"^.*xfs.*?", out, re.I):
        return "xfs"
    elif re.match (r"^.*FAT.*?", out, re.I):
        return "vfat"
    elif re.match (r"^.*NTFS.*?", out, re.I):
        return "ntfs-3g"
    else:
        raise Exception ("unknown fs: %s" % (out.strip ("\r\n")))

def get_mounted_fs_type (mount_point=None, dev_path=None):
    """ NOTE that /dev/main/vps00_root will actually be  /dev/mapper/main-vps00_root in /proc/mounts, so dev_path is not likely to be reliable
    """
    assert dev_path or mount_point
    if mount_point and mount_point != "/":
        mount_point = mount_point.rstrip ("/")
    f = open ("/proc/mounts", "r")
    lines = None
    try:
        lines = f.readlines ()
    finally:
        f.close ()
    lines.reverse ()
    for line in lines:
        arr = line.split ()
        if dev_path and arr[0] == dev_path:
            return arr[2]
        if mount_point and arr[1] == mount_point:
            return arr[2]
    if mount_point:
        raise Exception ("%s is not a mount point" % (mount_point))
    elif dev_path:
        raise Exception ("device %s is not mounted" % (dev_path))

def get_mountpoint (dev):
    f = open ("/proc/mounts", "r")
    lines = None
    try:
        lines = f.readlines ()
    finally:
        f.close ()
    lines.reverse ()
    for line in lines:
        arr = line.split ()
        if dev and arr[0] == dev:
            return arr[1]


def umount_tmp (tmp_mount):
    """ umount loop file and delete temporary mount point """
    call_cmd ("umount %s" % (tmp_mount))
    os.rmdir (tmp_mount)

def create_raw_image (path, size_g, sparse=False):
    assert size_g > 0
    size_m = int (size_g * 1024)
    if sparse:
        call_cmd ("dd if=/dev/zero of=%s bs=1M count=1 seek=%d" % (path, size_m - 1))
    else:
        call_cmd ("dd if=/dev/zero of=%s bs=1M count=%d" % (path, size_m))

def dd_file (in_file, out_file):
    assert os.path.exists (in_file)
    call_cmd ("dd if=%s of=%s" % (in_file, out_file))

def format_fs (fs_type, target):
    if fs_type in ['ext4', 'ext3', 'ext2']:
        mkfs_cmd = "mkfs.%s -F" % (fs_type)
    elif fs_type == 'reiserfs':
        mkfs_cmd = "mkfs.reiserfs -f"
    elif fs_type in ['swap']:
        mkfs_cmd = "mkswap"
    elif fs_type == 'raw':
        pass
    else:
        raise Exception ("not supported fs_type %s" % (fs_type))
    call_cmd ("%s %s" % (mkfs_cmd, target))


def sync_img (vpsmountpoint, template_img_path):
    if vpsmountpoint[-1] != '/':
        vpsmountpoint += "/"
    template_mount = mount_loop_tmp (template_img_path, readonly=True)
    if template_mount[-1] != '/':
        template_mount += "/"
    try:
        call_cmd ("rsync -a '%s/' '%s/'" % (template_mount, vpsmountpoint)) 
    finally:
        umount_tmp (template_mount)

def unpack_tarball (vpsmountpoint, tarball_path):
    pwd = os.getcwd()
    os.chdir (vpsmountpoint)
    try:
        if re.match ("^.*\.(tar\.gz|tgz)$", tarball_path):
            call_cmd ("tar zxf '%s'" % (tarball_path))
        elif re.match ('^.*\.(tar\.bz2|tbz2)$', tarball_path):
            call_cmd ("tar jxf '%s'" % (tarball_path))
    finally:
        os.chdir (pwd)

def vg_space (vg_name):
    out = call_cmd ("vgs --noheadings -o vg_free --units g --nosuffix /dev/%s" % (vg_name))
    out = out.strip ()
    free_space = int (float (out))
    out = call_cmd ("vgs --noheadings -o vg_size --units g --nosuffix /dev/%s" % (vg_name))
    out = out.strip ()
    total_space = int (float (out))
    return free_space, total_space


def lv_create (vg_name, lv_name, size_g):
    assert size_g > 0
    size_m = int (size_g * 1024)
    call_cmd ("lvcreate --name %s --size %dM /dev/%s" % (lv_name, size_m, vg_name))
    lv_dev = "/dev/%s/%s" % (vg_name, lv_name)
    if not os.path.exists (lv_dev):
        raise Exception ("lv %s not exists after creating" % (lv_dev))
    return lv_dev

def lv_delete (lv_dev):
    call_cmd ("lvremove -f %s" % (lv_dev))

def lv_rename (src_dev, dest_dev):
    call_cmd ("lvrename %s %s " % (src_dev, dest_dev))

def lv_getsize (dev):
    out = call_cmd ("lvs --noheadings -o lv_size --units g %s" % (dev))
    out = out.strip ()
    out = out.strip ("gG")
    return float(out)

def file_getsize (filename):
    # return in G
    s = os.stat (filename)
    return float (s.st_size) / 1024.0 / 1024.0 / 1024.0

def lv_get_mountpoint (dev):
    arr = dev.split ("/") 
    assert arr[0] == "" and arr[1] == 'dev' and len (arr) == 4
    if arr[2] != 'mapper':
        dev = "/dev/mapper/%s-%s" % (arr[2], arr[3])
    return get_mountpoint (dev)


def lv_snapshot (dev, snapshot_name, vg_name):
    snapshot_dev = "/dev/%s/%s" % (vg_name, snapshot_name)
    if not os.path.exists (dev):
        raise Exception ("%s not exists" % (dev))
    if os.path.exists (snapshot_dev):
        raise Exception ("%s already exists" % (snapshot_dev))
    size = lv_getsize (dev)
    call_cmd ("lvcreate --name %s --size %dG -s %s" % (snapshot_name, size, dev))
    return snapshot_dev

def pack_vps_fs_tarball (img_path, tarball_dir_or_path):
    """ if tarball_dir_or_path is a directory, will generate filename like XXX_fs_FSTYPE.tar.gz  """
    tarball_dir = None
    tarball_path = None
    if os.path.isdir (tarball_dir_or_path):
        tarball_dir = tarball_dir_or_path
    else:
        if os.path.exists (tarball_dir_or_path):
            raise Exception ("file %s exists" % (tarball_dir_or_path))
        tarball_path = tarball_dir_or_path
        tarball_dir = os.path.dirname (tarball_path)
        if not os.path.isdir (tarball_dir):
            raise Exception ("directory %s not exists" % (tarball_dir))

    if img_path.find ("/dev") == 0:
        mount_point = mount_partition_tmp (img_path, readonly=True)
    else:
        mount_point = mount_loop_tmp (img_path, readonly=True)
    if not tarball_path and tarball_dir:
        fs_type = get_fs_type (img_path)
        tarball_name = "%s_fs_%s.tar.gz" % (os.path.basename (img_path), fs_type)
        tarball_path = os.path.join (tarball_dir, tarball_name)
        if os.path.exists (tarball_path):
            raise Exception ("file %s already exists" % (tarball_path))
        
    cwd = os.getcwd ()
    os.chdir (mount_point)
    try:
        call_cmd ("tar zcf %s ." % (tarball_path))
    finally:
        os.chdir (cwd)
        umount_tmp (mount_point)
    return tarball_path

def get_fs_from_tarball_name (tarball_path):
    om = re.match (r"^.*?fs[_\-](\w+).*?$", os.path.basename (tarball_path))
    if not om:
        return None
    fs_type = om.group (1)
    return fs_type

def xm_network_attach (domain, vifname, mac, ip, bridge):
    call_cmd ("xm network-attach %s mac=%s ip=%s vifname=%s bridge=%s" % (domain, mac, ip, vifname, bridge))

def xm_network_detach (domain, mac):
    call_cmd ("xm network-detach %s %s" % (domain, mac))

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


if __name__ == '__main__':
    import unittest

    class TestVPSCommon (unittest.TestCase):

        def test_fs_from_tarball_name (self):
            self.assertEqual (get_fs_from_tarball_name ("/vps/ubuntu-11.10-amd64-fs-ext4.tar.gz"), "ext4")
            self.assertEqual (get_fs_from_tarball_name ("ubuntu_11.10_amd64_fs_ext4.tar.gz"), "ext4")
            self.assertEqual (get_fs_from_tarball_name ("ubuntu_11.10_amd64.tar.gz"), None)

    unittest.main ()
