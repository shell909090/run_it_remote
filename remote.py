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

    def __init__(self, finder, src, pathname, description):
        self.finder, self.src = finder, src
        self.pathname, self.description = pathname, description

    def exec_code_module(self, mod):
        exec compile(self.src, self.pathname, 'exec') in mod.__dict__

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
        loader = self.finder.find_remote('__init__', [self.pathname,])
        m = add_module(fullname)
        m.__file__ = loader.pathname
        m.__path__ = [self.pathname,]
        m.__package__ = fullname
        loader.exec_code_module(m)
        return m

class Finder(object):

    def __init__(self, channel):
        self.channel = channel

    def find_module(self, name, path):
        try: imp.find_module(name, path)
        except ImportError:
            r = self.find_remote(name, path)
            if r is not None: return r
            raise

    def find_remote(self, name, path):
        # print 'find remote:', name, path
        self.channel.write(['imp', name.split('.')[-1], path])
        r = self.channel.read()
        if r is not None: return self.type_map[r[2][2]](self, *r)

    type_map = {
        imp.PY_SOURCE: SrcLoader,
        imp.C_EXTENSION: ExtLoader,
        imp.PKG_DIRECTORY: PkgLoader}

class StdPipe(object):

    def __init__(self, channel):
        self.channel = channel

    def write(self, s):
        self.channel.write(['otpt', s])

    def flush(self):
        self.channel.write(['flsh', s])

class BaseChannel(object):

    def loop(self):
        self.g = {'__name__': '__remote__'}
        while True:
            o = self.read()
            if o[0] == 'exit': break
            if o[0] == 'aply':
                r = eval(o[1], self.g)(*o[2:])
            elif o[0] in ('exec', 'eval', 'single'):
                r = eval(compile(o[1], '<%s>' % o[0], o[0]), self.g)
            self.write(['rslt', r])

    def write(self, o):
        d = zlib.compress(marshal.dumps(o))
        self.stdout.write(struct.pack('>I', len(d)) + d)
        self.stdout.flush()

    def read(self):
        l = struct.unpack('>I', sys.stdin.read(4))[0]
        return marshal.loads(zlib.decompress(sys.stdin.read(l)))

class StdChannel(BaseChannel):

    def __init__(self):
        self.stdin, self.stdout = sys.stdin, os.fdopen(os.dup(1), 'w')
        os.close(1)
        os.dup2(2, 1)

class NetChannel(BaseChannel):

    def __init__(self, host, port):
        import socket
        self.listen = socket.socket()
        self.listen.bind((host, port))
        self.listen.listen(1)

    def loop(self):
        while True:
            self.sock, self.addr = self.listen.accept()
            self.stdout = self.stdin = self.sock.makefile('rw')
            BaseChannel.loop(self)

def main():
    import getopt
    optlist, args = getopt.getopt(sys.argv[1:], 'hn:')
    optdict = dict(optlist)
    if '-h' in optdict:
        print main.__doc__
        return

    global channel
    if '-n' in optdict:
        host, port = optdict['-n'].rsplit(':', 1)
        port = int(port)
        channel = NetChannel(host, port)
    else: channel = StdChannel()

    sys.modules['remote'] = __import__(__name__)
    sys.meta_path.append(Finder(channel))
    sys.stdout = StdPipe(channel)
    channel.loop()

if __name__ == '__main__': main()
