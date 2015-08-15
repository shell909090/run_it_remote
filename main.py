#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-08-14
@author: shell.xu
'''
import os, sys, imp, zlib, inspect, marshal, subprocess

BOOTSTRAP = '''import sys, marshal; exec compile(marshal.load(sys.stdin), '<core>', 'exec')'''

class LocalHost(object):

    def __init__(self):
        self.p = subprocess.Popen(
            ['python', '-c', BOOTSTRAP],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        with open('core.py', 'r') as fi:
            self.write(fi.read())

    def close(self):
        self.write(['exit',])
        self.p.wait()

    def write(self, o):
        marshal.dump(o, self.p.stdin)
        self.p.stdin.flush()

    def read(self):
        try:
            return marshal.load(self.p.stdout)
        except:
            print self.p.stderr.read()
            raise

    def loop(self):
        while True:
            r = self.read()
            if r[0] == 'otpt':
                sys.stdout.write(r[1])
            elif r[0] == 'flsh':
                sys.stdout.flush()
            elif r[0] == 'imp':
                try:
                    # print 'local find:', r
                    r = list(imp.find_module(r[1], r[2]))
                    # print 'local result:', r
                    if r[2][2] in (imp.PY_SOURCE, imp.C_EXTENSION):
                        with r[0]: r[0] = zlib.compress(r[0].read(), 9)
                    self.write(r)
                except ImportError: self.write(None)
            elif r[0] == 'rslt':
                return r[1]
            elif r[0] == 'excp':
                raise Exception(r[1])

    def eval(self, f):
        if hasattr(f, '__call__'):
            f = inspect.getsource(f)
        assert isinstance(f, basestring)
        self.write(['eval', f])
        return self.loop()

    def execute(self, f):
        if hasattr(f, '__call__'):
            f = inspect.getsource(f)
        assert isinstance(f, basestring)
        self.write(['exec', f])
        return self.loop()

class RemoteHost(LocalHost):

    def __init__(self, host):
        self.p = subprocess.Popen(
            ['ssh', host, 'python', '-c', '"%s"' % BOOTSTRAP],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        with open('core.py', 'r') as fi:
            self.write(fi.read())

def main():
    funcname = sys.argv[2]
    modname = funcname.rsplit('.', 1)[0]
    h = RemoteHost(sys.argv[1])
    h.execute('import ' + modname)
    r = h.eval(funcname + '()')
    h.close()
    print '----------output-----------'
    import pprint
    pprint.pprint(r)

if __name__ == '__main__': main()
