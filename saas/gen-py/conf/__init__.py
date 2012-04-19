import _env

import getpass
import socket
from zkit.jsdict import JsDict

import _load
import re

HOSTNAME = socket.gethostname()
HOST_ID  = re.search("\d+",HOSTNAME)
if HOST_ID: 
    HOST_ID = int(HOST_ID.group())
 
_load.load(
    JsDict(locals()),
    'default',
    'host.%s' % HOSTNAME,
#    'user.%s' % getpass.getuser(),
)



