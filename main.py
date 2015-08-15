#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-08-14
@author: shell.xu
'''
import os, sys, imp, zlib, getopt, socket, struct, pprint
import inspect, marshal, subprocess

BOOTSTRAP = '''import sys, zlib, marshal; exec compile(zlib.decompress(marshal.load(sys.stdin)), '<core>', 'exec')'''

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

    @staticmethod
    def check_f(f):
        if hasattr(f, '__call__'):
            f = inspect.getsource(f)
        assert isinstance(f, basestring)
        return f

    def eval(self, f):
        self.write(['eval', self.check_f(f)])
        return self.loop()

    def execute(self, f):
        self.write(['exec', self.check_f(f)])
        return self.loop()

    def call(self, f, *p):
        self.execute(f)
        return self.eval('%s(%s)' % (f.__name__, str(p)[1:-1]))

class ProcessInstance(BaseInstance):
    def start(self, cmd):
        self.p = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with open('core.py', 'r') as fi:
            marshal.dump(zlib.compress(fi.read(), 9), self.p.stdin)
            self.p.stdin.flush()

    def close(self):
        self.write(['exit',])
        self.p.wait()

    def write(self, o):
        d = zlib.compress(marshal.dumps(o), 9)
        self.p.stdin.write(struct.pack('>I', len(d)) + d)
        self.p.stdin.flush()

    def read(self):
        try:
            l = struct.unpack('>I', self.p.stdout.read(4))[0]
            return marshal.loads(zlib.decompress(self.p.stdout.read(l)))
        except:
            print self.p.stderr.read()
            raise

class LocalInstance(ProcessInstance):
    def __init__(self):
        self.start(['python', '-c', BOOTSTRAP])

    def __repr__(self): return '<local>'

class RemoteInstance(ProcessInstance):
    def __init__(self, host):
        self.host = host
        self.start(['ssh', host, 'python', '-c', '"%s"' % BOOTSTRAP])

    def __repr__(self): return self.host

class NetInstance(BaseInstance):
    def __init__(self, host, port):
        self.s = socket.socket()
        self.s.connect((host, port))
        self.stdin = self.stdout = self.s.makefile('rw')
        self.host = host

    def __repr__(self): return self.host

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

def main():
    optlist, args = getopt.getopt(sys.argv[1:], 'hn:m:')
    optdict = dict(optlist)
    if '-h' in optdict:
        print main.__doc__
        return

    ilist = []
    if '-n' in optdict:
        for addr in optdict['-n'].split(','):
            host, port = addr.rsplit(':', 1)
            port = int(port)
            ilist.append(NetInstance(host, port))
    else:
        for machine in optdict['-m'].split(','):
            ilist.append(RemoteInstance(machine))

    for funcname in args:
        modname = funcname.rsplit('.', 1)[0]
        for i in ilist:
            i.execute('import ' + modname)
            r = i.eval(funcname + '()')
            print '----------%s output: %s-----------' % (str(i), funcname)
            pprint.pprint(r)

    for i in ilist: i.close()

if __name__ == '__main__': main()
