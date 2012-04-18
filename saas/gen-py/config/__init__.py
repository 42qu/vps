import _env

from os.path import dirname, normpath, abspath, join

PREFIX = dirname(dirname(abspath(__file__)))

SSL_KEY_PEM = join(dirname(PREFIX),'private/key.pem')


