#!/usr/bin/env python

import os
import _env

from conf.os_image import OS_IMAGE_DICT


def find_os_image (os_id):
    v = OS_IMAGE_DICT.get (os_id)
    if not v or not isinstance (v, dict):
        raise Exception ("os_id=%s not supported" % str(os_id))
    image = v.get ("image")
    os_type = v.get ("os")
    version = v.get ("version")
    if not image or not os_type:
        raise Exception ("conf/os_image.py for os_id=%s invalid" % (os_id))
    os_type = os_type.lower ()
    if not os.path.isfile (image):
        raise Exception ("%s not exists" % (image))
    return (image, os_type, version)


