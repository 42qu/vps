#!/usr/bin/env python
#coding:utf-8


from zkit.reloader.reload_server import auto_reload
from client_vps import main
auto_reload(main)
