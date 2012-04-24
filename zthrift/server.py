#coding:utf-8
from conf import  SAAS_PORT, SAAS_HOST, SSL_CERT


from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer


def server(saas, handler):
    processor = saas.Processor(handler)

    from thrift.transport.TSSLSocket import TSSLServerSocket as  TServerSocket
    transport = TServerSocket(SAAS_HOST, port=SAAS_PORT, certfile=SSL_CERT)
    
#    from thrift.transport import TSocket 
#    transport = TSocket.TServerSocket(SAAS_HOST, port=SAAS_PORT)

    tfactory  = TTransport.TBufferedTransportFactory()
    pfactory  = TBinaryProtocol.TBinaryProtocolFactory()

    server    = TServer.TSimpleServer(processor, transport, tfactory, pfactory)

    # server = TServer.TThreadedServer(processor, transport, tfactory, pfactory)
    # server = TServer.TThreadPoolServer(processor, transport, tfactory, pfactory)
    server.serve()
