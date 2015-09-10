#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-09-09
@author: Shell.Xu
@copyright: 2015, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
import zlib
import base64
import struct
import marshal
import logging

def show_msg(action, o):
    if o is None:
        logging.debug('%s: none', action)
        return
    if isinstance(o, (int, long)):
        logging.debug('%s int: %d', action, o)
        return
    if isinstance(o, list):
        d = str(o)
        if len(d) >= 200:
            d = '["%s", ...]' % str(o[0])
        if len(d) >= 200:
            d = 'list too long'
    elif isinstance(o, basestring):
        d = o
        if len(d) >= 200:
            d = 'str too long'
    else:
        logging.debug('%s: unknown', action)
        return
    logging.debug('%s: %s', action, d)

class BaseEncoding(object):

    def __init__(self, chan, **kw):
        self.chan = chan

    def close(self):
        self.chan.close()

    def __repr__(self):
        return str(self.chan)

    def get_args(self):
        args = {}
        if hasattr(self.chan, 'get_args'):
            args = self.chan.get_args()
        return args

class BinaryEncoding(BaseEncoding):

    @staticmethod
    def get_bootstrap(d):
        return '''import sys, zlib, struct, marshal; l = struct.unpack('>I', sys.stdin.read(4))[0]; o = marshal.loads(zlib.decompress(sys.stdin.read(l))); exec compile(o, '<remote>', 'exec')'''

    def send(self, o):
        show_msg('send', o)
        d = zlib.compress(marshal.dumps(o), 9)
        self.chan.write(struct.pack('>I', len(d)) + d)

    def recv(self):
        l = struct.unpack('>I', self.chan.read(4))[0]
        o = marshal.loads(zlib.decompress(self.chan.read(l)))
        show_msg('recv', o)
        return o

class Base64Encoding(BaseEncoding):

    @staticmethod
    def get_bootstrap(d):
        return '''import sys, zlib, base64, struct, marshal; l = struct.unpack('>I', base64.b64decode(sys.stdin.read(8)))[0]; o = marshal.loads(zlib.decompress(base64.b64decode(sys.stdin.read(l)))); exec compile(o, '<remote>', 'exec')'''

    @staticmethod
    def get_args(kw):
        kw.update({'protocol': 'Base64Encoding'})
        return kw

    def send(self, o):
        show_msg('send', o)
        d = base64.b64encode(zlib.compress(marshal.dumps(o), 9))
        self.chan.write(base64.b64encode(struct.pack('>I', len(d))) + d)

    def recv(self):
        l = struct.unpack('>I', base64.b64decode(self.chan.read(8)))[0]
        o = marshal.loads(zlib.decompress(base64.b64decode(self.chan.read(l))))
        show_msg('recv', o)
        return o
