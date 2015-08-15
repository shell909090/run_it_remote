#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-08-14
@author: shell.xu
'''
import os, sys, imp, zlib, struct, marshal

def add_module(name):
    if name not in sys.modules:
        sys.modules[name] = imp.new_module(name)
    return sys.modules[name]

class Loader(object):
    def __init__(self, src, pathname, description):
        self.src, self.pathname, self.description = src, pathname, description
    def exec_code_module(self, mod):
        co = compile(self.src, self.pathname, 'exec')
        exec co in mod.__dict__

class SrcLoader(Loader):
    def load_module(self, fullname):
        m = add_module(fullname)
        m.__file__ = self.pathname
        self.exec_code_module(m)
        return m

class ExtLoader(Loader):
    def load_module(self, fullname):
        import tempfile
        with tempfile.NamedTemporaryFile('wb') as tmp:
            tmp.write(self.src)
            tmp.flush()
            return imp.load_dynamic(fullname, tmp.name)

class PkgLoader(Loader):
    def load_module(self, fullname):
        loader = finder.find_remote('__init__', [self.pathname,])
        m = add_module(fullname)
        m.__file__ = loader.pathname
        m.__path__ = [self.pathname,]
        m.__package__ = fullname
        loader.exec_code_module(m)
        return m

class Finder(object):
    def find_module(self, name, path):
        try: imp.find_module(name, path)
        except ImportError:
            r = self.find_remote(name, path)
            if r is None: raise
            return r
    def find_remote(self, name, path):
        # print 'find remote:', name, path
        write(['imp', name.split('.')[-1], path])
        r = read()
        if r is not None: return self.type_map[r[2][2]](*r)
    type_map = {
        imp.PY_SOURCE: SrcLoader,
        imp.C_EXTENSION: ExtLoader,
        imp.PKG_DIRECTORY: PkgLoader}

finder = Finder()
sys.meta_path.append(finder)

class StdPipe(object):
    def write(self, s): write(['otpt', s])
    def flush(self): write(['flsh', s])
sys.stdout = StdPipe()

def loop():
    g = dict()
    while True:
        o = read()
        if o[0] == 'exit': break
        if o[0] == 'exec': co = compile(o[1], '<exec>', 'exec')
        elif o[0] == 'eval': co = compile(o[1], '<eval>', 'eval')
        write(['rslt', eval(co, g)])

def main_exec():
    stdout = os.fdopen(os.dup(1), 'w')
    os.close(1)
    os.dup2(2, 1)
    global write
    def write(o):
        d = zlib.compress(marshal.dumps(o))
        stdout.write(struct.pack('>I', len(d)) + d)
        stdout.flush()
    global read
    def read():
        l = struct.unpack('>I', sys.stdin.read(4))[0]
        return marshal.loads(zlib.decompress(sys.stdin.read(l)))
    return loop()

def main_net(host, port):
    global write
    global read
    import socket
    l = socket.socket()
    l.bind((host, port))
    l.listen(1)
    while True:
        s, a = l.accept()
        f = s.makefile('rw')
        def write(o):
            d = zlib.compress(marshal.dumps(o))
            f.write(struct.pack('>I', len(d)) + d)
            f.flush()
        def read():
            l = struct.unpack('>I', f.read(4))[0]
            return marshal.loads(zlib.decompress(f.read(l)))
        loop()

def main():
    import getopt
    optlist, args = getopt.getopt(sys.argv[1:], 'hn:')
    optdict = dict(optlist)
    if '-h' in optdict:
        print main.__doc__
        return

    if '-n' in optdict:
        host, port = optdict['-n'].rsplit(':', 1)
        port = int(port)
        main_net(host, port)
    else: main_exec()

if __name__ == '__main__': main()
