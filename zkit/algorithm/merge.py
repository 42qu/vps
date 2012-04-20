#!/usr/bin/env python
#coding:utf-8
from heapq import heappop, _siftup, heapify
from bisect import insort

def imerge_reversed(*iterables):
    """Merge multiple reversedly sorted inputs into a single reversed sorted
    output.

    Equivalent to:  sorted(itertools.chain(*iterables), reverse=True)

    """
    insort_right = insort
    h = []
    h_append = h.append
    for it in iterables:
        try:
            next = iter(it).next
            h_append((next(), next))
        except StopIteration:
            pass
    h.sort()

    while 1:
        try:
            v, next = h.pop()
            yield v
            insort_right(h, (next(), next))
        except StopIteration:
            pass
        except IndexError:
            return


def imerge(*iterables):
    ''' http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/491285
    Merge multiple sorted inputs into a single sorted output.

    Equivalent to:  sorted(itertools.chain(*iterables))

    >>> list(imerge([1,3,5,7], [0,2,4,8], [5,10,15,20], [], [25]))
    [0, 1, 2, 3, 4, 5, 5, 7, 8, 10, 15, 20, 25]

    '''

    h = []
    h_append = h.append
    for it in map(iter, iterables):
        try:
            next = it.next
            h_append([next(), next])
        except StopIteration:
            pass
    heapify(h)

    while True:
        try:
            while True:
                v, next = s = h[0]      # raises IndexError when h is empty
                yield v
                s[0] = next()           # raises StopIteration when exhausted
                _siftup(h, 0)            # restore heap condition
        except StopIteration:
            heappop(h)                  # remove empty iterator
        except IndexError:
            return


if __name__ == '__main__':
    class O(object):
        def __init__(self, create_time):
            self.create_time = create_time

        def __cmp__(self, other):
            return self.create_time > other.create_time

    def main():
        for i in imerge(map(O, [1, 3, 5, 7]), map(O, [0, 2, 4, 8]), map(O, [5, 10, 15, 20])):
            print i.create_time
    main()
