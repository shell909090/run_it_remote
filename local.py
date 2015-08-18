#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-08-14
@author: shell.xu
'''
import os, sys, imp, zlib, struct, marshal
import inspect

BOOTSTRAP = '''import sys, zlib, struct, marshal; l = struct.unpack('>I', sys.stdin.read(4))[0]; src = marshal.loads(zlib.decompress(sys.stdin.read(l))); exec compile(src, '<remote>', 'exec')'''

class BaseInstance(object):

    def loop(self):
        while True:
            r = self.read()
            if r[0] == 'otpt':
                sys.stdout.write(r[1])
            elif r[0] == 'flsh':
                sys.stdout.flush()
            elif r[0] == 'imp':
                self.find_module(r[1], r[2])
            elif r[0] == 'rslt':
                return r[1]
            elif r[0] == 'excp':
                raise Exception(r[1])

    def find_module(self, name, path):
        try:
            r = list(imp.find_module(name, path))
            if r[2][2] in (imp.PY_SOURCE, imp.C_EXTENSION):
                with r[0]: r[0] = r[0].read()
            self.write(r)
        except ImportError: self.write(None)

    def eval(self, f):
        self.write(['eval', f])
        return self.loop()

    def execute(self, f):
        self.write(['exec', f])
        return self.loop()

    def single(self, f):
        self.write(['single', f])
        return self.loop()

    def apply(self, f, *p):
        self.write(['aply', self.sendfunc(f)] + list(p))
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
        with open('remote.py', 'r') as fi:
            self.write(fi.read())

    def close(self):
        self.write(['exit',])
        self.p.wait()

    def write(self, o):
        # print 'out', o
        d = zlib.compress(marshal.dumps(o), 9)
        self.p.stdin.write(struct.pack('>I', len(d)) + d)
        self.p.stdin.flush()

    def read(self):
        try:
            l = struct.unpack('>I', self.p.stdout.read(4))[0]
            o = marshal.loads(zlib.decompress(self.p.stdout.read(l)))
            # print 'in', o[0]
            return o
        except:
            print self.p.stderr.read()
            raise

class LocalInstance(ProcessInstance):

    def __init__(self):
        self.start(['python', '-c', BOOTSTRAP])

    def __repr__(self): return '<local>'

class SshInstance(ProcessInstance):

    def __init__(self, host):
        self.host = host
        self.start(['ssh', host, 'python', '-c', '"%s"' % BOOTSTRAP])

    def __repr__(self): return self.host

class NetInstance(BaseInstance):

    def __init__(self, addr):
        host, port = addr.rsplit(':', 1)
        port = int(port)
        import socket
        self.s = socket.socket()
        self.s.connect((host, port))
        self.stdin = self.stdout = self.s.makefile('rw')
        self.addr = addr

    def __repr__(self): return self.addr

    def close(self):
        self.write(['exit',])
        self.stdin.close()

    def write(self, o):
        d = zlib.compress(marshal.dumps(o), 9)
        self.stdin.write(struct.pack('>I', len(d)) + d)
        self.stdin.flush()

    def read(self):
        l = struct.unpack('>I', self.stdout.read(4))[0]
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
            self.ins.write(['aply', self.fmaps[f]] + list(p))
            return self.ins.loop()
        return inner

    def bind(self, ins):
        self.ins = ins
        for f in self.funcs:
            self.fmaps[f] = ins.sendfunc(f)

def run_parallel(func, it, concurrent=20):
    from multiprocessing.pool import ThreadPool
    pool = ThreadPool(concurrent)
    for i in it:
        pool.apply_async(func, (i,))
    pool.close()
    pool.join()

def main():
    import getopt
    optlist, args = getopt.getopt(sys.argv[1:], 'hn:m:p')
    optdict = dict(optlist)
    if '-h' in optdict:
        print main.__doc__
        return

    def runner(ins):
        for command in args:
            print '-----%s output: %s-----' % (str(ins), command)
            ins.single(command)
        ins.close()

    def runmode(inscls, l):
        if '-p' in optdict:
            return run_parallel(lambda x: runner(inscls(x)), l.split(','))
        for x in l.split(','):
            runner(inscls(x))

    if '-n' in optdict:
        runmode(NetInstance, optdict['-n'])
    elif '-m' in optdict:
        runmode(SshInstance, optdict['-m'])
    else:
        print 'neither network(-n) nor machine(-m) in parameters, quit.'
        return

if __name__ == '__main__': main()
