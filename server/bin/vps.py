#!/usr/bin/env python
import _env
import conf

def main():
    from zthrift.server import server
    from saas import VPS
    from server.ctrl.vps import Handler

    print 'server runing ...'
    server(VPS, Handler(), allowed_ips=conf.ALLOWED_IPS)
    print 'done'

if __name__ == "__main__":
    main()

