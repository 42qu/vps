#!/usr/bin/env python
#coding:utf-8

from config import SSL_KEY_PEM, SAAS_PORT, SAAS_HOST

from thrift import Thrift
from thrift.transport import TSSLSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

def client(saas, handler):
    try:
        # Make socket
        transport = TSSLSocket.TSSLSocket(SAAS_HOST, SAAS_PORT, ca_certs=SSL_KEY_PEM)

        # Buffering is critical. Raw sockets are very slow
        transport = TTransport.TBufferedTransport(transport)

        # Wrap in a protocol
        protocol = TBinaryProtocol.TBinaryProtocol(transport)
        client = saas.Client(protocol)

        # Connect!
        transport.open()
        handler(client)
        transport.close()


    except Thrift.TException, tx:
        print '%s' % (tx.message)


