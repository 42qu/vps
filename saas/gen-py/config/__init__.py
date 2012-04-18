import _env
from os.path import dirname, normpath, abspath, join
PREFIX = dirname(dirname(abspath(__file__)))
import sys
sys.path.append(PREFIX)

import getpass
import socket
from zkit.jsdict import JsDict


import _load 
_load.load(
    JsDict(locals()),
    'default',
    'host.%s' % socket.gethostname(),
#    'user.%s' % getpass.getuser(),
)



