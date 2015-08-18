#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-08-14
@author: shell.xu
'''
import os, sys, imp, zlib, struct, marshal

CHUNK_SIZE = 64000

def add_module(name):
    if name not in sys.modules:
        sys.modules[name] = imp.new_module(name)
    return sys.modules[name]

class Loader(object):

    def __init__(self, finder, srcfid, pathname, description):
        self.finder, self.srcfile = finder, None
        self.pathname, self.description = pathname, description
        if srcfid is not None:
            self.srcfile = ChannelFile(finder.channel, srcfid)

    def exec_code_module(self, mod):
        if not hasattr(self, 'src'):
            self.src = self.srcfile.read()
            self.srcfile.close()
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
        self.channel.send(['find_module', name.split('.')[-1], path])
        r = self.channel.recv()
        if r is not None: return self.type_map[r[2][2]](self, *r)

    type_map = {
        imp.PY_SOURCE: SrcLoader,
        imp.C_EXTENSION: ExtLoader,
        imp.PKG_DIRECTORY: PkgLoader}

class ChannelFile(object):

    def __init__(self, channel, id):
        self.channel, self.id = channel, id

    def write(self, s):
        s = str(s)
        while s:
            d, s = s[:CHUNK_SIZE], s[CHUNK_SIZE:]
            self.channel.send(['write', self.id, d])

    def read(self, size=-1):
        d = ''
        while len(d) < size or size == -1:
            if size == -1: l = CHUNK_SIZE
            else: l = size - len(d)
            if l > CHUNK_SIZE: l = CHUNK_SIZE
            self.channel.send(['read', self.id, l])
            r = self.channel.recv()
            d += r
            if len(r) == 0: return d

    def seek(self, offset, whence):
        self.channel.send(['seek', self.id, offset, whence])

    def flush(self):
        self.channel.send(['flush', self.id])

    def close(self):
        self.channel.send(['close', self.id])

class BaseChannel(object):

    def __init__(self): self.g = dict()

    def loop(self):
        while True:
            o = self.recv()
            if o[0] == 'exit': break
            if o[0] == 'result': return o[1]
            if o[0] == 'apply':
                r = eval(o[1], self.g)(*o[2:])
            elif o[0] in ('exec', 'eval', 'single'):
                r = eval(compile(o[1], '<%s>' % o[0], o[0]), self.g)
            self.send(['result', r])

    def send(self, o):
        d = zlib.compress(marshal.dumps(o))
        self.stdout.write(struct.pack('>H', len(d)) + d)
        self.stdout.flush()

    def recv(self):
        l = struct.unpack('>H', sys.stdin.read(2))[0]
        return marshal.loads(zlib.decompress(sys.stdin.read(l)))

    def open(self, filepath, mode):
        self.send(['open', filepath, mode])
        r = self.recv()
        if r[0] != 'fid': raise Exception(r)
        return ChannelFile(self, r[1])

    def getstd(self, which):
        self.send(['std', which])
        r = self.recv()
        if r[0] != 'fid': raise Exception(r)
        return ChannelFile(self, r[1])

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
        import inspect
        m = inspect.getmodule(f)
        fname = f.__name__
        if m is None:
            self.execute('import __main__')
            fname = '__main__.' + fname
        else:
            self.execute('import ' + m.__name__)
            fname = m.__name__ + '.' + fname
        return fname

class StdChannel(BaseChannel):

    def __init__(self):
        BaseChannel.__init__(self)
        self.stdin, self.stdout = sys.stdin, os.fdopen(os.dup(1), 'w')
        os.close(1)
        os.dup2(2, 1)

class NetChannel(BaseChannel):

    def __init__(self, host, port):
        BaseChannel.__init__(self)
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
    sys.stdout = channel.getstd('stdout')
    channel.send(['result', None])
    channel.loop()

if __name__ == '__main__': main()
