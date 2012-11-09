#!/usr/bin/env python

import os
import time

from string import Template
from ops.vps_store import vps_store_new, vps_store_clone, VPSStoreBase
from ops.vps_netinf import VPSNet, VPSNetExt, VPSNetInt
import ops.vps_common as vps_common
import ops.xen as xen
import lib.diff as diff
import ops._env
import conf
assert conf.XEN_CONFIG_DIR
assert conf.XEN_AUTO_DIR
assert conf.DEFAULT_FS_TYPE
assert conf.VPS_METADATA_DIR
assert conf.MOUNT_POINT_DIR



class XenVPS (object):
    """ needs root to run xen command """

    xen_inf = None
    name = None
    root_store = None
    swap_store = None
    config_path = None
    auto_config_path = None
    xen_bridge = None
    has_all_attr = False
    vcpu = None
    mem_m = None
    disk_g = None
    ip = None # main ip
    netmask = None # main ip netmask
    gateway = None
    template_image = None
    root_pw = None
    data_disks = None
    os_id = None

    def __init__ (self, _id):
        assert isinstance (_id, int)
        self.vps_id = _id
        self.name = "vps%s" % (str(_id).zfill (2)) # to be compatible with current practice standard
        self.config_path = os.path.join (conf.XEN_CONFIG_DIR, self.name)
        self.auto_config_path = os.path.join (conf.XEN_AUTO_DIR, self.name)
        self.save_path = os.path.join (conf.MOUNT_POINT_DIR, "%s.save" % self.name)
        self.xen_bridge = conf.XEN_BRIDGE
        self.has_all_attr = False
        self.xen_inf = xen.get_xen_inf ()
        self.vif_ext_name = self.name
        self.vif_int_name = self.name + "int"
        self.data_disks = {}
        self.trash_disks = {}
        self.vifs = {}

    vif_ext = property (lambda self: self.vifs.get (self.vif_ext_name))

    vif_int = property (lambda self: self.vifs.get (self.vif_int_name))
    

    def clone (self):
        new = self.__class__ (self.vps_id)
        new.setup (self.os_id, self.vcpu, self.mem_m, self.root_store.size_g, None, 
                 self.swap_store.size_g)
        new.ip = self.ip
        new.netmask = self.netmask
        new.gateway = self.gateway
        for disk in self.data_disks.values ():
            new.data_disks[disk.xen_dev] = vps_store_clone (disk)
        #TODO  trash_disks
        for vif in self.vifs.values ():
            new.vifs[vif.ifname] = vif.clone ()
        return new

    def to_meta (self):
        data = {}
        data['vps_id'] = self.vps_id
        data['os_id'] = self.os_id
        data['vcpu'] = self.vcpu
        data['mem_m'] = self.mem_m
        data['root_size_g'] = self.root_store.size_g
        data['swap_size_g'] = self.swap_store.size_g
        data['root_xen_dev'] = self.root_store.xen_dev
        data['gateway'] = self.gateway
        data['ip'] = self.ip
        data['netmask'] = self.netmask
        disks = []
        for disk in self.data_disks.itervalues ():
            if disk.xen_dev != self.root_store.xen_dev:
                disk_data = disk.to_meta ()
                assert disk_data
                disks.append (disk_data)
        data['data_disks'] = disks
        data['trash_disks'] = map (lambda disk:disk.to_meta (), self.trash_disks.values ())
        vifs = []
        for vif in self.vifs.itervalues ():
            vif_data = vif.to_meta ()
            assert vif_data
            vifs.append (vif_data)
        data['vifs'] = vifs
        return data

    @classmethod
    def from_meta (cls, data):
        assert data
        try:
            self = cls (data['vps_id'])
            self.setup (data['os_id'], data['vcpu'], data['mem_m'], data['root_size_g'], None, 
                    data['swap_size_g'])
            self.gateway = data['gateway']
            self.ip = data['ip']
            self.netmask = data['netmask']
            if data.has_key ('data_disks'):
                for _disk in data['data_disks']:
                    disk = VPSStoreBase.from_meta (_disk)
                    assert disk
                    self.data_disks[disk.xen_dev] = disk
            if data.has_key ('trash_disks'):
                for _trash in data['trash_disks']:
                    trash = VPSStoreBase.from_meta (_trash)
                    assert _trash
                    self.trash_disks[trash.xen_dev] = trash
            for _vif in data['vifs']:
                vif = VPSNet.from_meta (_vif)
                self.vifs[vif.ifname] = vif
        except KeyError, e:
            raise Exception ("metadata missing key %s" % (str(e)))
        return self

    def setup (self, os_id, vcpu, mem_m, disk_g, root_pw=None, swp_g=None, gateway=None):
        """ on error will raise Exception """
        assert mem_m > 0 and vcpu > 0
        self.has_all_attr = True
        self.os_id = os_id
        self.vcpu = vcpu
        self.mem_m = mem_m
        if swp_g is not None:
            swp_g = swp_g
        else:
            if self.mem_m >= 2000:
                swp_g = 2
            else:
                swp_g = 1
        self.gateway = gateway
        self.root_store = vps_store_new ("%s_root" % self.name, "xvda1", None, '/', disk_g)
        self.swap_store = vps_store_new ("%s_swap" % self.name, "xvda2", 'swap', 'none', swp_g)
        self.data_disks[self.root_store.xen_dev] = self.root_store
        self.root_pw = root_pw
        
    def get_xendev_by_id (self, disk_id):
        return "xvdc%d" % (disk_id)

    def add_extra_storage (self, disk_id, size_g, fs_type=conf.DEFAULT_FS_TYPE):
        assert disk_id > 0
        assert size_g > 0
        xen_dev = self.get_xendev_by_id (disk_id)
        mount_point = '/mnt/data%d' % (disk_id)
        partition_name = "%s_data%s" % (self.name, disk_id)
        self.data_disks[xen_dev] = vps_store_new (partition_name, xen_dev, fs_type, mount_point, size_g)

    def delete_trash (self, disk):
        del self.trash_disks[disk.xen_dev]

    def dump_storage_to_trash (self, disk, expire_days=10):
        res = False
        if disk.exists ():
            disk.dump_trash ()
            res = True
        try:
            del self.data_disks[disk.xen_dev]
        except KeyError:
            pass
        self.trash_disks[disk.xen_dev] = disk
        return res

    def renew_storage (self, xen_dev, expire_days=5, new_size=None):
        # move old disk to trash, return the (old_disk, new_disk)
        old_disk = self.root_store
        old_disk.dump_trash (expire_days)
        self.trash_disks[old_disk.xen_dev] = old_disk
        if not new_size:
            new_size = old_disk.size_g
        new_disk = vps_store_new (old_disk.partition_name, old_disk.xen_dev, old_disk.fs_type, old_disk.mount_point, new_size)
        self.data_disks[new_disk.xen_dev] = new_disk
        return old_disk, new_disk
        
    def recover_storage_from_trash (self, disk):
        res = False
        if disk.trash_exists ():
            disk.restore_from_trash ()
            res = True
        elif disk.exists ():
            pass
        else:
            raise Exception ("disk %d not found in trash" % (str(disk)))
        self.data_disks[disk.xen_dev] = disk
        try:
            del self.trash_disks[disk.xen_dev]
        except KeyError:
            pass
        return res

    def has_netinf (self, vifname):
        return self.vifs.has_key (vifname)

    def add_netinf_ext (self, ip_dict, mac=None, bandwidth=0):
        # ip_dict: ip=>netmask
        assert isinstance (ip_dict, dict)
        ips = ip_dict.keys ()
        assert len(ips) > 0
        ips.sort ()
        self.ip = ips[0]
        mac = mac or vps_common.gen_mac ()
        vif = VPSNetExt (self.vif_ext_name, ip_dict, mac=mac, bandwidth=bandwidth)
        self.vifs[self.vif_ext_name] = vif
        return vif

    def add_netinf_int (self, ip_dict, mac=None, bandwidth=0):
        # ip_dict: ip=>netmask
        assert isinstance (ip_dict, dict)
        ips = ip_dict.keys ()
        assert len(ips) > 0
        ips.sort ()
        if not self.ip:
            self.ip = ips[0]
        mac = mac or vps_common.gen_mac ()
        vif = VPSNetInt (self.vif_int_name, ip_dict, mac=mac, bandwidth=bandwidth)
        self.vifs[self.vif_int_name] = vif
        return vif

    def del_netinf (self, vifname):
        vif = self.vifs[vifname]

    def check_resource_avail (self, ignore_trash=False):
        """ on error or space not available raise Exception """
        assert self.has_all_attr
        if self.is_running ():
            raise Exception ("check resource: %s is running, no need to create" % (self.name))
        mem_free = self.xen_inf.mem_free ()
        if self.mem_m > mem_free:
            raise Exception ("check resource: xen free memory is not enough  (%dM left < %dM)" % (mem_free, self.mem_m))
        #check disks not implemented, too complicate, expect error throw during vps creation
        # check ip available
        if self.ip:
            if 0 == os.system ("ping -c2 -W1 %s >/dev/null" % (self.ip)):
                raise Exception ("check resource: ip %s is in use" % (self.ip))
        if self.gateway:
            if os.system ("ping -c2 -W1 %s >/dev/null" % (self.gateway)):
                raise Exception ("check resource: gateway %s is not reachable" % (self.gateway))
        if not ignore_trash:
            if os.path.exists (self.config_path):
                raise Exception ("check resource: %s already exists" % (self.config_path))
            if self.root_store.exists ():
                raise Exception ("check resource: %s already exists" % (str(self.root_store)))
            if self.swap_store.exists ():
                raise Exception ("check resource: %s already exists" % (str(self.swap_store)))

    def gen_xenpv_config (self):
        assert self.has_all_attr
        # must called after setup ()

        all_t = Template ("""
bootloader = "/usr/bin/pygrub"
name = "$name"
vcpus = "$vcpu"
maxmem = "$mem"
memory = "$mem"
vif = [ $vifs ]
disk = [ $disks ]
root = "/dev/xvda1"
extra = "fastboot $extra_boot_param"
on_shutdown = "destroy"
on_poweroff = "destroy"
on_reboot = "restart"
on_crash = "restart"
""" )

        vif_t = Template ("""  "vifname=$ifname,mac=$mac,ip=$ip,bridge=$bridge"$rate  """)
        disk_t = Template (""" "$path,$dev,$mod" """)
        disks = []
        vifs = []
        disk_keys = self.data_disks.keys ()
        disk_keys.sort ()
        disks.append (disk_t.substitute (path=self.root_store.xen_path, dev=self.root_store.xen_dev, mod="w") )
        if self.swap_store.size_g > 0:
            disks.append ( disk_t.substitute (path=self.swap_store.xen_path, dev=self.swap_store.xen_dev, mod="w") )
        for k in disk_keys:
            data_disk = self.data_disks[k]
            if k != self.root_store.xen_dev:
                disks.append ( disk_t.substitute (path=data_disk.xen_path, dev=data_disk.xen_dev, mod="w") )
        vif_keys = self.vifs.keys ()
        vif_keys.sort ()
        for k in vif_keys:
            vif = self.vifs[k]
            ips = vif.ip_dict.keys ()
            ips.sort ()
            if conf.USE_OVS or not vif.bandwidth:
                vifs.append ( vif_t.substitute (ifname=vif.ifname, mac=vif.mac, ip=" ".join (ips), bridge=vif.bridge, rate="") )
            else:
                vifs.append ( vif_t.substitute (ifname=vif.ifname, mac=vif.mac, ip=" ".join (ips), bridge=vif.bridge, 
                    rate=",rate=%dMb/s" % vif.bandwidth) )
        if self.os_id != 1:  # centos 5.8
            extra_boot_param = " independent_wallclock=1 "
        else:
            extra_boot_param = ""
        xen_config = all_t.substitute (name=self.name, vcpu=str(self.vcpu), mem=str(self.mem_m), 
                    disks=",".join (disks), vifs=",".join (vifs), extra_boot_param=extra_boot_param,
                )
        return xen_config
       
    def is_running (self):
        return self.xen_inf.is_running (self.name)

    def start (self):
        if self.is_running ():
            return
        self.xen_inf.create (self.config_path)
        start_ts = time.time ()
        while True:
            time.sleep (1)
            if self.is_running ():
                return 
            now = time.time ()
            if now - start_ts > 5:
                raise Exception ("failed to create domain %s" % (self.name))


    def stop (self):
        """ shutdown a vps, because os needs time to shutdown, will wait for 30 sec until it's really not running
            if shutdowned, returns True, otherwise return False
        """
        if not self.is_running ():
            return True
        self.xen_inf.shutdown (self.name)
        start_ts = time.time ()
        while True:
            time.sleep (1)
            if not self.is_running ():
                return True
            now = time.time ()
            if now - start_ts > 90:
                # shutdown failed
                return False

    def save (self):
        if self.is_running():
            if os.path.isfile (self.save_path):
                os.remove (self.save_path)
            self.xen_inf.save (self.name, self.save_path)
        if not os.path.isfile (self.save_path):
            raise Exception ("cannot save %s" % (self.name))

    def restore (self):
        if self.is_running():
            raise Exception ("cannot restore %s, vps is running" % (self.name))
        elif os.path.isfile (self.save_path):
            self.xen_inf.restore (self.save_path)
        else:
            raise Exception ("%s does not exists" % (self.save_path))

    def destroy (self):
        """ if failed to destroy, raise Exception """
        self.xen_inf.destroy (self.name)
        start_ts = time.time ()
        while True:
            time.sleep (1)
            if not self.is_running ():
                return
            now = time.time ()
            if now - start_ts > 5:
                raise Exception ("cannot destroy %s after 5 sec" % (self.name))


    def wait_until_reachable (self, timeout=20):
        """ wait for the vps to be reachable and return True, or timeout returns False"""
        start_ts = time.time ()
        if not self.ip:
            raise Exception ("%s has no ip, vps object not properly setup" % (self.name))
        while True:
            time.sleep (1)
            if 0 == os.system ("ping -c1 -W1 %s>/dev/null" % (self.ip)):
                return True
            now = time.time ()
            if now - start_ts > timeout:
                return False

    def create_autolink (self):
        if os.path.exists(self.auto_config_path):
            if os.path.islink (self.auto_config_path):
                dest = os.readlink (self.auto_config_path)
                if not os.path.isabs (dest):
                    dest = os.path.join (os.path.dirname(self.auto_config_path), dest)
                if dest == os.path.abspath(self.config_path):
                    return
                os.remove (self.auto_config_path)
            else:
                raise Exception ("a non link file %s is blocking link creation" % (self.auto_config_path))
        os.symlink(self.config_path, self.auto_config_path)

    def check_storage_integrity (self):
        for disk in self.data_disks.values ():
            if not disk.exists ():
                raise Exception ("disk %s not exists" % (str(disk)))
        if self.swap_store.size_g > 0:
            if not self.swap_store.exists ():
                raise Exception ("disk %s not exists" % (str(self.swap_store)))

    def get_nonexisting_trash (self):
        result = []
        for disk in self.trash_disks.values ():
            if not disk.trash_exists ():
                result.append (disk)
        return result
        
#    def check_trash_integrity (self):
#        for trash_disk in self.trash_disks.values ():
#            if not trash_disk.trash_exists ():
#                raise Exception ("trash_disk %s not exists" % (str(trash_disk)))

    def check_xen_config (self):
        if not os.path.exists (self.config_path):
            raise Exception ("%s not found" % self.config_path)
        f = open (self.config_path, "r")
        content = None
        try:
            content = "".join (f.readlines ())
        finally:
            f.close ()
        regular_xen_config = self.gen_xenpv_config ()
        diff_res = diff.readable_unified (content, regular_xen_config, name1=self.config_path, name2="generated_xen_config")
        if diff_res != "":
            raise Exception ("xen config not regular: [%s]" % diff_res)


        
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
