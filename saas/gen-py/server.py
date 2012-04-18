#!/usr/bin/env python
#coding:utf-8

from config import SSL_KEY_PEM , SAAS_PORT


from saas import VPS
from saas.ttypes import Action


from thrift.transport.TSSLSocket import TSSLServerSocket as  TServerSocket

from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

class Handler(object):
    def to_do(self, pc):
        pass

    def info(self, id):
        pass

    def opened(self, id):
        pass

    def closed(self, id):
        pass

    def restart(self, id):
        pass


transport = TServerSocket(port=SAAS_PORT, certfile=SSL_KEY_PEM)
tfactory  = TTransport.TBufferedTransportFactory()
pfactory  = TBinaryProtocol.TBinaryProtocolFactory()

handler   = Handler()
processor = VPS.Processor(handler)
server    = TServer.TSimpleServer(processor, transport, tfactory, pfactory)

# server = TServer.TThreadedServer(processor, transport, tfactory, pfactory)
# server = TServer.TThreadPoolServer(processor, transport, tfactory, pfactory)

print 'serving ...'
server.serve()
print 'done'


