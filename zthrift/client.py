#!/usr/bin/env python


from conf import SAAS_PORT, SAAS_HOST

from thrift import Thrift
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

from thrift.transport.TSocket import TSocket
from thrift.transport.TSSLSocket import TSSLSocket 

def get_client (saas, host=SAAS_HOST, port=SAAS_PORT, timeout_ms=5000):
    sock = TSSLSocket(host, port, ca_certs=None, validate=False)
    sock.setTimeout (timeout_ms)
#    sock = TSocket(SAAS_HOST, SAAS_PORT)
#    transport = TTransport.TBufferedTransport(sock)
    transport = TTransport.TFramedTransport (sock)
    protocol = TBinaryProtocol.TBinaryProtocol(transport)
    client = saas.Client(protocol)
    return transport, client



#def run_client (saas, client_func, *args):
#    assert callable (client_func)
#    res = None
#    try:
#        transport.open()
#        res = client_func (client, *args)
#        return res
#    finally:
#        if transport is not None:
#            transport.close()

