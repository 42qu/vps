#!/usr/bin/env python
# coding:utf-8


import _env
import conf
from lib.socket_engine_ssl import SSLSocketEngine, Connection
from lib.net_io import send_all, recv_all, NetHead
import socket
import threading
import random
import time
from lib.log import Log, getLogger
import lib.io_poll as iopoll
#from lib.conn_pool import *
import os
import traceback
import ssl
#from lib.timecache import TimeCache

SSL_CERT = os.path.join(os.path.dirname(__file__), '../conf/private/server.pem')

data = "".join (["0" for i in xrange (0, 10000)])
global_lock = threading.Lock ()

server_addr = ("0.0.0.0", 20300)
round = 50

g_send_count = 0
g_client_num = 200
#g_client_num = 2
g_done_client = 0

#tc = TimeCache (0.5)

def client_ssl ():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    global g_send_count, g_client_num, g_done_client, server_addr, global_lock
    global data
    global round
    sock = ssl.wrap_socket (sock)
    sock.connect (server_addr)
#        times = random.randint (1, 5000)
#        time.sleep (times/ 2000.0)
    for i in xrange (0, round):
        print i
        send_all (sock, data)
        _data = recv_all (sock, len(data))
        if _data == data:
            global_lock.acquire ()
            g_send_count += 1
            global_lock.release ()
        else:
            print "client recv invalid data"
#            time.sleep (0.01)
    print "client done", g_done_client
    sock.close ()
    global_lock.acquire ()
    g_done_client += 1
    global_lock.release ()


def start_unblock_server_ssl ():
    global server_addr
    poll = None
    if 'EPoll' in dir(iopoll):
        poll = iopoll.EPoll (True)
        print "using epoll et mode"
    else:
        poll = iopoll.Poll ()
    server = SSLSocketEngine (poll, SSL_CERT, is_blocking=False, debug=True)
    server.set_logger (getLogger ("server"))
#    server.get_time = tc.time

    def _on_err (conn):
        raise conn.error

    def _on_send (conn):
        #print "on send"
        server.watch_conn (conn)
        return
    def _on_recv (conn):
        #print "on_recv"
        server.remove_conn (conn)
        server.write_unblock (conn, conn.get_readbuf (), _on_send, _on_err)
        return
    server.listen_addr (server_addr, server.read_unblock, (len(data), _on_recv, None))

    def _run (_server):
        while True:
            try:
                _server.poll ()
            except Exception, e:
                traceback.print_exc ()
                os._exit (1)
        return
    th = threading.Thread (target=_run, args=(server,))
    th.setDaemon (1)
    th.start ()
    return server
    
 
def test_client ():
    global g_send_count, g_done_client, g_client_num
##    pool = ConnPool (10, -1)
    i = 0
    ths = list ()
    start_time = time.time ()
    while True:
        if i < g_client_num:
#            ths.append (threading.Thread (target=client_pool, args=(pool, )))
            ths.append (threading.Thread (target=client_ssl, args=()))
            ths[i].setDaemon(1)
            ths[i].start ()
            i += 1
        else:
            for j in xrange (0, i):
                ths[j].join ()

            print "time:", time.time () - start_time
            print g_done_client, g_send_count
#           pool.clear_conn (server_addr)

            if g_client_num == g_done_client:
                print "test OK"
                os._exit (0)
            else:
                print "test fail"
            return

def test_client_unblock ():
    poll = None
    if 'EPoll' in dir(iopoll):
        poll = iopoll.EPoll (True)
        print "client using epoll et mode"
    else:
        poll = iopoll.Poll ()
    engine = SSLSocketEngine (poll, SSL_CERT, debug=True)
#    engine.get_time = tc.time
    engine.set_logger (getLogger ("client"))
    start_time = time.time ()
    def __on_conn_err (e, client_id):
        print "client", client_id, "connect error", str(e)
        os._exit (1)
        return
    def __on_err (conn, client_id, count):
        print client_id, count, type(conn.error), conn.error
        raise conn.error
        return
    def __on_recv (conn, client_id, count):
#        print count
        global g_done_client
        if count >= 0:
            buf = conn.get_readbuf ()
            if buf != data:
                print "data recv invalid, client:", client, "data:", buf
                os._exit (0)
        if count < round:
            print "send", client_id, count + 1
            engine.write_unblock (conn, data, __on_send, __on_err, (client_id, count + 1))
        else:
            engine.close_conn (conn)
            g_done_client += 1
            print "client", client_id, "done"
            if g_done_client == g_client_num:
                print "test client done time: ", time.time() - start_time
        return
    def __on_send ( conn, client_id, count):
        engine.read_unblock (conn, len(data), __on_recv, __on_err, (client_id, count))
        return
    def __on_conn (sock, client_id):
        print "ssl conn"
        __on_recv (Connection (sock), client_id, -1)
        return
    def _run (engine):
        global g_done_client
        while g_done_client < g_client_num:
            try:
                engine.poll ()
            except Exception, e:
                traceback.print_exc ()
                os._exit (1)
        print g_done_client
        return
    print "client_unblock started"
    for i in xrange (0, g_client_num):
        engine.connect_unblock_ssl (server_addr, __on_conn, __on_conn_err, (i,))
    _run (engine)  


def main ():

    Log ("client", config=conf)
    Log ("server", config=conf)
    server = start_unblock_server_ssl ()
    time.sleep (1)
#    test_client ()
    test_client_unblock ()



if __name__ == '__main__':
    main ()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
