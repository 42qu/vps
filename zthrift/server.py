#coding:utf-8
from conf import  SAAS_PORT, SAAS_HOST, SSL_CERT

import thrift
from thrift.transport.TSocket import TSocket
from thrift.transport.TSSLSocket import TSSLServerSocket
from thrift.transport.TSocket import TServerSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

#import ssl

#class MySSLServerSocket (TSSLServerSocket):
#
#    def accept(self):
#        plain_client, addr = self.handle.accept()
#        try:
#            client = ssl.wrap_socket(plain_client, certfile=self.certfile,
#                          server_side=True, ssl_version=self.SSL_VERSION)
#        except (ssl.SSLError), e:
#            print type (e), e
#          # failed handshake/ssl wrap, close socket to client
#            plain_client.close()
#            return None
#        result = TSocket()
#        result.setHandle(client)
#        return result

def server(saas, handler, host=None):
    processor = saas.Processor(handler)

#    transport = TServerSocket(host, port=SAAS_PORT)
#    transport = MySSLServerSocket(host, port=SAAS_PORT, certfile=SSL_CERT)
    transport = TSSLServerSocket(host, port=SAAS_PORT, certfile=SSL_CERT)

    tfactory  = TTransport.TBufferedTransportFactory()
    pfactory  = TBinaryProtocol.TBinaryProtocolFactory()

    server    = TServer.TSimpleServer(processor, transport, tfactory, pfactory)

    # server = TServer.TThreadedServer(processor, transport, tfactory, pfactory)
    # server = TServer.TThreadPoolServer(processor, transport, tfactory, pfactory)
    server.serve()
