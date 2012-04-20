#!/usr/bin/env python


from conf import SSL_KEY_PEM , SAAS_PORT, SAAS_HOST

from thrift import Thrift
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

from thrift.transport.TSocket import TSocket
from thrift.transport.TSSLSocket import TSSLSocket 


def run_client (saas, handler):
    assert callable (handler)
    transport = None
    try:
#        sock = TSSLSocket(SAAS_HOST, SAAS_PORT, ca_certs=SSL_KEY_PEM)
        sock = TSocket(SAAS_HOST, SAAS_PORT)

        transport = TTransport.TBufferedTransport(sock)
        protocol = TBinaryProtocol.TBinaryProtocol(transport)
        client = saas.Client(protocol)

        transport.open()
        handler(client)
    finally:
        if transport is not None:
            transport.close()

