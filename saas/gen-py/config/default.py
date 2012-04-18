#!/usr/bin/env python
# -*- coding: utf-8 -*-


def prepare(o):
    from os.path import join, dirname
    from _env import PREFIX
    
    o.SSL_KEY_PEM = join(dirname(PREFIX),'private/key.pem')
    o.SAAS_PORT = 50042

    o.SAAS_HOST = "saas-vps.42qu.us"

    return o


def finish(o):
    return o

