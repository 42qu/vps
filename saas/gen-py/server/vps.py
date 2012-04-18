#!/usr/bin/env python
import _env

def main():
    from zthrift.server import server
    from saas import VPS
    from ctrl.vps import Handler

    print 'server runing ...'
    server(VPS, Handler())
    print 'done'

if __name__ == "__main__":
    main()

