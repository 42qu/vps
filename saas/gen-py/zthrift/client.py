#!/usr/bin/env python


from config import SSL_KEY_PEM , SAAS_PORT, SAAS_HOST

from thrift import Thrift
from thrift.transport.TSSLSocket import TSSLSocket 
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

def client(saas, handler):
    try:
        transport = TSSLSocket(SAAS_HOST, SAAS_PORT, ca_certs=SSL_KEY_PEM)
        transport = TTransport.TBufferedTransport(transport)
        protocol = TBinaryProtocol.TBinaryProtocol(transport)
        client = saas.Client(protocol)

        transport.open()

        handler(client)
        transport.close()

    except Thrift.TException, tx:
        print '%s' % (tx.message)


