#!/usr/bin/env python
# coding:utf-8

class Enum (object):

    def __init__ (self, **k_args):
        self._pair = dict(k_args)
        self._VALUES_TO_NAMES = dict ()
        for k, v in self._pair.iteritems ():
            self._VALUES_TO_NAMES[v] = k
    
    def __getattr__ (self, name):
        return self._pair[name]

    def _get_name (self, _id):
        return self._VALUES_TO_NAMES.get (_id)

if __name__ == '__main__':
    CMD = Enum (A=1, B=2)
    print CMD.A, CMD.B
    print CMD._VALUES_TO_NAMES.get (1)


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
