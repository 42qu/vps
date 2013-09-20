#!/usr/bin/env python

import difflib



def readable_unified(text1, text2, name1="a", name2="b"):
    lines1 = text1.splitlines(True)
    lines2 = text2.splitlines(True)
    arr = []
    for line in difflib.unified_diff(lines1, lines2, fromfile=name1, tofile=name2):
        if line[-1] != '\n':
            arr.append(line + "[no end of line]\n")
        else:
            arr.append(line)
    return "".join(arr)
        

if __name__ == '__main__':

    res = readable_unified("aaa\nbbb\n", "aaa\nccc\n")
    print "[%s]" % (res)
    
    res = readable_unified("aaa\nbbb", "aaa\nbbb\n")
    print "[%s]" % (res)
    assert readable_unified("aaa\n", "aaa\n") == ''
    




# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
