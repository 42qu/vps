#coding:utf-8
from config import SSL_KEY_PEM , SAAS_PORT, SAAS_HOST

from thrift.transport.TSSLSocket import TSSLServerSocket as  TServerSocket

from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer


def server(saas, handler):
    processor = saas.Processor(handler)

    transport = TServerSocket(SAAS_HOST, SAAS_PORT, certfile=SSL_KEY_PEM)
    tfactory  = TTransport.TBufferedTransportFactory()
    pfactory  = TBinaryProtocol.TBinaryProtocolFactory()

    server    = TServer.TSimpleServer(processor, transport, tfactory, pfactory)

    # server = TServer.TThreadedServer(processor, transport, tfactory, pfactory)
    # server = TServer.TThreadPoolServer(processor, transport, tfactory, pfactory)
    server.serve()
