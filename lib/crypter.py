#!/usr/bin/env python
# coding:utf-8

from Crypto.Cipher import AES
from Crypto import Random

def fix_len(s, byte_len):
    l = len(s)
    if l < byte_len:
        return  s + (byte_len - l) * 'x'
    elif l > byte_len:
        return s[0 : byte_len]
    else:
        return s

def random_string(n):
    return Random.new().read(n)


class AESCryptor(object):

    def __init__(self, key, iv, block_size):
        self.byte_len = block_size / 8
        self.key = fix_len(key, self.byte_len)
        self.iv = fix_len(iv, self.byte_len)
        self.cy_obj = AES.new(self.key, AES.MODE_CFB, self.iv)

    def encrypt(self, data):
        return self.cy_obj.encrypt(data)

    def decrypt(self, buf):
        return self.cy_obj.decrypt(buf)


if __name__ == '__main__':
    ss = random_string(32)
    assert len(ss) == 32
    arr = [random_string(8), random_string(35), random_string(133)]
    aes_key = "dsf343242"
    c1 = AESCryptor(aes_key, "aaa", 128)
    c2 = AESCryptor(aes_key, "aaa", 128)
    for i in arr:
        b1 = c1.encrypt(i)
        b2 = c2.decrypt(b1)
        assert i == b2
        print i



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
