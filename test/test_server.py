#!/usr/bin/env python

import _env
import conf
from lib.socket_engine import TCPSocketEngine, Connection
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
#from lib.timecache import TimeCache

data = "".join (["0" for i in xrange (0, 10000)])
global_lock = threading.Lock ()

server_addr = ("0.0.0.0", 20300)
round = 5000

g_send_count = 0
g_client_num = 10
g_done_client = 0

#tc = TimeCache (0.5)



def client ():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    global g_send_count, g_client_num, g_done_client, server_addr, global_lock
    global data
    global round
    sock.connect (server_addr)
#        times = random.randint (1, 5000)
#        time.sleep (times/ 2000.0)
    for i in xrange (0, round):
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

def client_pool (pool):
    global g_send_count, g_client_num, g_done_client, server_addr, global_lock
    global data
    global round
    conn = None
    try:
        for i in xrange (0, round):
            conn = pool.get_conn (server_addr)
            if conn == None:
                print "get_conn failed"
                return
            send_all (conn.sock, data)
            _data = recv_all (conn.sock, len(data))
            global_lock.acquire ()
            g_send_count += 1
            global_lock.release ()
            pool.put_back (conn)
        global_lock.acquire ()
        g_done_client += 1
        global_lock.release ()
        print "client done", g_done_client
    except Exception, e:
        getLogger ("client").exception_ex ("client: " + str (e))
        print "client: ", str (e)
        if conn:
            pool.put_back (conn, True)
            print "put_back conn , is_err=True"
        return
    


def start_block_server ():
    global server_addr
    server = TCPSocketEngine (iopoll.Poll (), is_blocking=True, debug=False)
    server.set_logger (getLogger ("server"))

    def server_handler (conn):
        sock = conn.sock
        try:
            _data = recv_all (sock, len (data))
            send_all (sock, _data)
#            server.watch_conn (conn)
        except Exception, e:
            print "server handler", str (e)
            getLogger ("server").exception (str (e))
            server.close_conn (conn)
            return False

    server.listen_addr (server_addr, server_handler)

    def _run (server):
        while True:
            try:
                server.poll ()
            except Exception, e:
                traceback.print_exc ()
                os._exit (1)
        return
    th = threading.Thread (target=_run, args=(server,))
    th.setDaemon (1)
    th.start ()
    print "block server started"
    return server
    

def start_unblock_server ():
    global server_addr
    poll = None
    if 'EPoll' in dir(iopoll):
        poll = iopoll.EPoll (True)
        print "using epoll et mode"
    else:
        poll = iopoll.Poll ()
    server = TCPSocketEngine (poll, is_blocking=False, debug=False)
    server.set_logger (getLogger ("server"))
#    server.get_time = tc.time

    def _on_send (conn):
        #print "on send"
        server.watch_conn (conn)
        return
    def _on_recv (conn):
        #print "on_recv"
        server.remove_conn (conn)
        server.write_unblock (conn, conn.get_readbuf (), _on_send, None)
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
            ths.append (threading.Thread (target=client, args=()))
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
    engine = TCPSocketEngine (poll, debug=False)
#    engine.get_time = tc.time
    engine.set_logger (getLogger ("client"))
    start_time = time.time ()
    def __on_conn_err (e, client_id):
        print client_id, "connect error", str(e)
        os._exit (1)
        return
    def __on_err (conn, client_id, count):
        print client_id, "error", str(conn.error), count
        return
    def __on_recv (conn, client_id, count):
        global g_done_client
        if count >= 0:
            buf = conn.get_readbuf ()
            if buf != data:
                print "data recv invalid, client:", client, "data:", buf
                os._exit (0)
        if count < round:
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
        engine.connect_unblock (server_addr, __on_conn, __on_conn_err, (i,))
    _run (engine)  


def main ():
    Log ("client", config=conf)
    Log ("server", config=conf)
    server = start_unblock_server ()
#    server = start_block_server ()
    time.sleep (1)
#    test_client ()
    test_client_unblock ()


if __name__ == '__main__':
#    import yappi
#    yappi.start()
    main ()
#    stats = yappi.get_stats()
#    for stat in stats:
#        print stat
#    yappi.stop()
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
