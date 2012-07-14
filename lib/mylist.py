#!/usr/bin/env python

# for providing a unify interface between collection deque or list

has_deque = False
try:
    import collections
    if 'deque' in dir (collections):
        has_deque = True
except ImportError:
    pass

if has_deque:
    class MyList (collections.deque):
        pass
else:
    class MyList (list):

        def popleft (self):
            return self.pop (0)

        def appendleft (self, v):
            return self.insert (0, v)



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
