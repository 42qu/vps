import _env

import getpass
import socket
from zkit.jsdict import JsDict

import _load
import re

HOSTNAME = socket.gethostname()
 
_load.load(
    JsDict(locals()),
    'default',
    'host.%s' % HOSTNAME,
#    'user.%s' % getpass.getuser(),
)



