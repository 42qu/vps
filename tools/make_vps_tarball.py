#!/usr/bin/env python

import sys
import os
import _env
import ops.vps_common as vps_common
from lib.command import call_cmd
import conf
assert conf.OS_IMAGE_DIR and os.path.isdir (conf.OS_IMAGE_DIR)


def usage ():
    print """usage: \n%s [image_path/partion_path] [tarball_dir]
""" % (sys.argv[0])


def main():
    if len(sys.argv) < 3:
        usage ()
        os._exit (0)
    img_path = sys.argv[1]
    tarball_dir = sys.argv[2]

    if not os.path.exists (img_path):
        print "%s not exists" % (img_path)
        os._exit (1)
    if not os.path.isdir (tarball_dir):
        print '%s is not a directory' % (tarball_dir)
        os._exit (1)
    tarball_path = vps_common.pack_vps_tarball (img_path, tarball_dir)
    print "%s packed in %s" % (img_path, tarball_path)
    
if "__main__" == __name__:
    main()

