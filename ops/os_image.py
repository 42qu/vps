#!/usr/bin/env python

import os
import _env

import conf
assert isinstance (conf.OS_IMAGE_DICT, dict)

def find_os_image (os_id):
    v = conf.OS_IMAGE_DICT.get (os_id)
    if not v or not isinstance (v, dict):
        raise Exception ("os_id=%s not supported" % str(os_id))
    image = v.get ("image")
    os_type = v.get ("os")
    version = v.get ("version")
    if not image or not os_type:
        raise Exception ("conf/os_image.py for os_id=%s invalid" % (os_id))
    os_type = os_type.lower ()
    image_path = os.path.join (conf.os_image_dir, image)
    if not os.path.isfile (image_path):
        raise Exception ("%s not exists" % (image_path))
    return (image_path, os_type, version)


