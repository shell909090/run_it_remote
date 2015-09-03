#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-08-14
@author: shell.xu
@copyright: 2015, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
import os
import sys
import imp
import zlib
import base64
import struct
import marshal
import inspect
import logging
from os import path

def show_msg(action, o):
    if isinstance(o, list):
        logging.debug('%s: %s', action, str(o))
    elif isinstance(o, (int, long)):
        logging.debug('%s int: %d', action, o)
    elif isinstance(o, basestring):
        logging.debug('%s str: %d', action, len(o))
    else:
        logging.debug('%s: unknown', action)

class BinaryEncoding(object):

    BOOTSTRAP = '''import sys, zlib, struct, marshal; l = struct.unpack('>I', sys.stdin.read(4))[0]; o = marshal.loads(zlib.decompress(sys.stdin.read(l))); exec compile(o, '<remote>', 'exec')'''

    def send(self, o):
        show_msg('send', o)
        d = zlib.compress(marshal.dumps(o), 9)
        self.write(struct.pack('>I', len(d)) + d)

    def recv(self):
        l = struct.unpack('>I', self.read(4))[0]
        o = marshal.loads(zlib.decompress(self.read(l)))
        show_msg('recv', o)
        return o

class Base64Encoding(object):

    BOOTSTRAP = '''import sys, zlib, base64, struct, marshal; l = struct.unpack('>I', base64.b64decode(sys.stdin.read(8)))[0]; o = marshal.loads(zlib.decompress(base64.b64decode(sys.stdin.read(l)))); exec compile(o, '<remote>', 'exec')'''

    def translate_remote(self, d):
        return d.replace('StdChannel, BinaryEncoding', 'StdChannel, Base64Encoding')
    
    def send(self, o):
        show_msg('send', o)
        d = base64.b64encode(zlib.compress(marshal.dumps(o), 9))
        self.write(base64.b64encode(struct.pack('>I', len(d))) + d)

    def recv(self):
        l = struct.unpack('>I', base64.b64decode(self.read(8)))[0]
        o = marshal.loads(zlib.decompress(base64.b64decode(self.read(l))))
        show_msg('recv', o)
        return o

class ProcessChannel(object):

    def __init__(self, cmd):
        import subprocess
        self.p = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def close(self):
        self.p.wait()

    def write(self, d):
        try:
            self.p.stdin.write(d)
            self.p.stdin.flush()
        except:
            print self.p.stderr.read()
            raise

    def read(self, n):
        try:
            return self.p.stdout.read(n)
        except:
            print self.p.stderr.read()
            raise

class LocalChannel(ProcessChannel):

    def __init__(self):
        ProcessChannel.__init__(self, ['python', '-c', BOOTSTRAP])

    def __repr__(self):
        return '<local>'

class SshChannel(ProcessChannel):

    def __init__(self, host):
        ProcessChannel.__init__(self, ['ssh', host, 'python', '-c', '"%s"' % self.BOOTSTRAP])
        self.host = host

    def __repr__(self):
        return self.host

class SshSudoChannel(ProcessChannel):

    def __init__(self, host, user=None):
        if user:
            cmd = ['ssh', host, 'sudo', '-u', user,
                   'python', '-c', '"%s"' % self.BOOTSTRAP]
        else:
            cmd = ['ssh', host, 'sudo',
                   'python', '-c', '"%s"' % self.BOOTSTRAP]
        ProcessChannel.__init__(self, cmd)
        self.host, self.user = host, user

    def __repr__(self):
        return self.host

class Remote(object):

    def __init__(self, chan):
        self.chan = chan
        self.g, self.fmaps = {}, {}

        basedir = path.dirname(__file__)
        with open(path.join(basedir, 'remote.py'), 'r') as fi:
            d = fi.read()
        if hasattr(self.chan, 'translate_remote'):
            d = self.chan.translate_remote(d)
        self.chan.send(d)
        self.loop()

    def __repr__(self):
        return str(self.chan)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        self.chan.send(['exit',])
        self.chan.close()

    def loop(self):
        while True:
            o = self.chan.recv()
            if o[0] == 'result':
                return o[1]
            if o[0] == 'apply':
                r = eval(o[1], self.g)(*o[2:])
                self.chan.send(['result', r])
            elif o[0] in ('exec', 'eval', 'single'):
                r = eval(compile(o[1], '<%s>' % o[0], o[0]), self.g)
                self.chan.send(['result', r])
            else:
                getattr(self, 'on_' + o[0])(*o[1:])

    def on_open(self, filepath, mode):
        f = open(filepath, mode)
        self.fmaps[id(f)] = f
        self.chan.send(id(f))

    def on_std(self, which):
        if which == 'stdout':
            f = sys.stdout
        elif which == 'stderr':
            f = sys.stderr
        elif which == 'stdin':
            f = sys.stdin
        else:
            raise Exception('unknown std: %s' % which)
        self.fmaps[id(f)] = f
        self.chan.send(id(f))

    def on_write(self, id, d):
        self.fmaps[id].write(d)

    def on_read(self, id, size):
        d = self.fmaps[id].read(size)
        self.chan.send(d)

    def on_seek(self, id, offset, whence):
        self.fmaps[id].seek(offset, whence)

    def on_flush(self, id):
        self.fmaps[id].flush()

    def on_close(self, id):
        f = self.fmaps[id]
        if f not in (sys.stdin, sys.stdout, sys.stderr):
            f.close()
        del self.fmaps[id]

    def on_find_module(self, name, path):
        try:
            r = list(imp.find_module(name, path))
            if r[0] is not None:
                self.fmaps[id(r[0])] = r[0]
                r[0] = id(r[0])
            self.chan.send(r)
        except ImportError: self.chan.send(None)

    def on_except(self, err):
        raise Exception(err)

    def eval(self, f):
        self.chan.send(['eval', f])
        return self.loop()

    def execute(self, f):
        self.chan.send(['exec', f])
        return self.loop()

    def single(self, f):
        self.chan.send(['single', f])
        return self.loop()

    def apply(self, f, *p):
        self.chan.send(['apply', self.sendfunc(f)] + list(p))
        return self.loop()

    def sendfunc(self, f):
        m = inspect.getmodule(f)
        fname = f.__name__
        if m.__name__ == '__main__':
            self.execute(inspect.getsource(m))
        else:
            self.execute('import ' + m.__name__)
            fname = m.__name__ + '.' + fname
        return fname
