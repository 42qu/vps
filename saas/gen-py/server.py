#!/usr/bin/env python
#coding:utf-8

from config import SSL_KEY_PEM , SAAS_PORT


from saas import VPS 
from saas.ttypes import Action

from shared.ttypes import SharedStruct

from thrift.transport import TSSLSocket
# __init__(self, host=None, port=9090, certfile='cert.pem', unix_socket=None)
 
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

class CalculatorHandler:
    def __init__(self):
        self.log = {}

    def ping(self):
        print 'ping()'

    def add(self, n1, n2):
        print 'add(%d,%d)' % (n1, n2)
        return n1+n2

    def calculate(self, logid, work):
        print 'calculate(%d, %r)' % (logid, work)

        if work.op == Operation.ADD:
            val = work.num1 + work.num2
        elif work.op == Operation.SUBTRACT:
            val = work.num1 - work.num2
        elif work.op == Operation.MULTIPLY:
            val = work.num1 * work.num2
        elif work.op == Operation.DIVIDE:
            if work.num2 == 0:
                x = InvalidOperation()
                x.what = work.op
                x.why = 'Cannot divide by 0'
                raise x
            val = work.num1 / work.num2
        else:
            x = InvalidOperation()
            x.what = work.op
            x.why = 'Invalid operation'
            raise x

        log = SharedStruct()
        log.key = logid
        log.value = '%d' % (val)
        self.log[logid] = log

        return val

    def getStruct(self, key):
        print 'getStruct(%d)' % (key)
        return self.log[key]

    def zip(self):
        print 'zip()'

handler = CalculatorHandler()
processor = Calculator.Processor(handler)
transport = TSocket.TServerSocket(9090)
tfactory = TTransport.TBufferedTransportFactory()
pfactory = TBinaryProtocol.TBinaryProtocolFactory()

server = TServer.TSimpleServer(processor, transport, tfactory, pfactory)

# You could do one of these for a multithreaded server
#server = TServer.TThreadedServer(processor, transport, tfactory, pfactory)
#server = TServer.TThreadPoolServer(processor, transport, tfactory, pfactory)

print 'Starting the server...'
server.serve()
print 'done.'
