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
import struct
import marshal
import inspect
import logging
from os import path

BOOTSTRAP = '''import sys, zlib, struct, marshal; exec compile(marshal.loads(zlib.decompress(sys.stdin.read(struct.unpack('>I', sys.stdin.read(4))[0]))), '<remote>', 'exec')'''
CHUNK_SIZE = 2147483647

class BaseInstance(object):

    def __init__(self):
        self.g, self.fmaps = {}, {}

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_value, traceback): self.close()

    def loop(self):
        while True:
            o = self.recv()
            if o[0] == 'result': return o[1]
            if o[0] == 'apply':
                r = eval(o[1], self.g)(*o[2:])
                self.send(['result', r])
            elif o[0] in ('exec', 'eval', 'single'):
                r = eval(compile(o[1], '<%s>' % o[0], o[0]), self.g)
                self.send(['result', r])
            else: getattr(self, 'on_' + o[0])(*o[1:])

    def on_open(self, filepath, mode):
        f = open(filepath, mode)
        self.fmaps[id(f)] = f
        self.send(id(f))

    def on_std(self, which):
        if which == 'stdout': f = sys.stdout
        elif which == 'stderr': f = sys.stderr
        elif which == 'stdin': f = sys.stdin
        self.fmaps[id(f)] = f
        self.send(id(f))

    def on_write(self, id, d):
        self.fmaps[id].write(d)

    def on_read(self, id, size):
        d = self.fmaps[id].read(size)
        self.send(d)
        # while size > 0 or size == -1:
        #     l = size
        #     if l > CHUNK_SIZE or l < 0: l = CHUNK_SIZE
        #     print self.fmaps[id], l
        #     d = self.fmaps[id].read(l)
        #     self.send(d)
        #     if len(d) == 0: return
        #     if size != -1: size -= len(d)

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
            self.send(r)
        except ImportError: self.send(None)

    def on_except(self, err):
        raise Exception(err)

    def eval(self, f):
        self.send(['eval', f])
        return self.loop()

    def execute(self, f):
        self.send(['exec', f])
        return self.loop()

    def single(self, f):
        self.send(['single', f])
        return self.loop()

    def apply(self, f, *p):
        self.send(['apply', self.sendfunc(f)] + list(p))
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

class ProcessInstance(BaseInstance):

    def start(self, cmd):
        import subprocess
        self.p = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        basedir = path.dirname(__file__)
        with open(path.join(basedir, 'remote.py'), 'r') as fi:
            self.send(fi.read())
        self.loop()

    def close(self):
        self.send(['exit',])
        self.p.wait()

    def send(self, o):
        if isinstance(o, list):
            logging.debug('send: %s', str(o))
        else: logging.debug('send: data')
        d = zlib.compress(marshal.dumps(o), 9)
        self.p.stdin.write(struct.pack('>I', len(d)) + d)
        self.p.stdin.flush()

    def recv(self):
        try:
            l = struct.unpack('>I', self.p.stdout.read(4))[0]
            o = marshal.loads(zlib.decompress(self.p.stdout.read(l)))
            if isinstance(o, list): logging.debug('recv: %s', str(o))
            else: logging.debug('recv: data')
            return o
        except:
            print self.p.stderr.read()
            raise

class LocalInstance(ProcessInstance):

    def __init__(self):
        ProcessInstance.__init__(self)
        self.start(['python', '-c', BOOTSTRAP])

    def __repr__(self): return '<local>'

class SshInstance(ProcessInstance):

    def __init__(self, host):
        ProcessInstance.__init__(self)
        self.host = host
        self.start(['ssh', host, 'python', '-c', '"%s"' % BOOTSTRAP])

    def __repr__(self): return self.host

class SudoSshInstance(ProcessInstance):

    def __init__(self, host, user=None):
        ProcessInstance.__init__(self)
        self.host, self.user = host, user
        if user:
            self.start(['ssh', host, 'sudo', '-u', user,
                        'python', '-c', '"%s"' % BOOTSTRAP])
        else:
            self.start(['ssh', host, 'sudo',
                        'python', '-c', '"%s"' % BOOTSTRAP])

    def __repr__(self): return self.host

class NetInstance(BaseInstance):

    def __init__(self, addr):
        BaseInstance.__init__(self)
        host, port = addr.rsplit(':', 1)
        port = int(port)
        import socket
        self.s = socket.socket()
        self.s.connect((host, port))
        self.stdin = self.stdout = self.s.makefile('rw')
        self.addr = addr

    def __repr__(self): return self.addr

    def close(self):
        self.send(['exit',])
        self.stdin.close()

    def send(self, o):
        d = zlib.compress(marshal.dumps(o), 9)
        self.stdin.write(struct.pack('>I', len(d)) + d)
        self.stdin.flush()

    def recv(self):
        l = struct.unpack('>I', self.stdout.read(2))[0]
        return marshal.loads(zlib.decompress(self.stdout.read(l)))

class RemoteFunction(object):

    def __init__(self):
        self.funcs = set()
        self.fmaps = dict()

    def func(self, f):
        import remote
        if hasattr(remote, 'channel'): return f

        self.funcs.add(f)
        def inner(*p):
            if f not in self.fmaps:
                raise Exception('not bind yet.')
            self.ins.send(['apply', self.fmaps[f]] + list(p))
            return self.ins.loop()
        return inner

    def bind(self, ins):
        self.ins = ins
        for f in self.funcs:
            self.fmaps[f] = ins.sendfunc(f)
