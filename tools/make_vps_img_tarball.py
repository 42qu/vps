#!/usr/bin/env python

import sys
import os
import _env
import ops.vps_common as vps_common
import conf
assert conf.OS_IMAGE_DIR and os.path.isdir (conf.OS_IMAGE_DIR)
import ops.os_init as os_init


def usage ():
    print """usage: \n%s [image_path/partion_path] [os] [version] [arch]
""" % (sys.argv[0])


def main():
    if len(sys.argv) < 5:
        usage ()
        os._exit (0)
    img_path = sys.argv[1]
    os_release = sys.argv[2]
    version = sys.argv[3]
    arch = sys.argv[4]

    tarball_path = os.path.join (conf.OS_IMAGE_DIR, "%s-%s-%s.tar.gz" % (os_release, version, arch))
    if not os.path.exists (img_path):
        print "%s not exists" % (img_path)
        os._exit (1)
    if os.path.exists (tarball_path):
        answer = raw_input ('%s exists, override ? [y/n]' % (tarball_path))
        if answer not in ['y', 'Y']:
            print "aborted"
            os._exit (0)
        os.unlink (tarball_path)
    os_init.pack_vps_fs_tarball (img_path, tarball_path, is_image=True)
    print "done"

    
if "__main__" == __name__:
    main()

