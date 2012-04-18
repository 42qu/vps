import _env

import default
import getpass
import socket
from jsdict import JsDict

default.load(
    JsDict(locals()),
    'host.%s' % socket.gethostname(),
    'user.%s' % getpass.getuser(),
)



