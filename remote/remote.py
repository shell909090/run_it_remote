#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-08-14
@author: shell.xu
@copyright: 2015, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
import os, sys, imp, zlib, base64, struct, marshal

Args = {} # replace Parameter here.

def add_module(name):
    if name not in sys.modules:
        sys.modules[name] = imp.new_module(name)
    return sys.modules[name]

class Loader(object):

    def __init__(self, finder, src, pathname, description):
        self.finder, self.src = finder, src
        self.pathname = pathname
        self.description = description

    def exec_code_module(self, mod):
        exec compile(self.src, self.pathname, 'exec') in mod.__dict__

class SrcLoader(Loader):

    def load_module(self, fullname):
        m = add_module(fullname)
        m.__file__ = self.pathname
        self.exec_code_module(m)
        return m

class PycLoader(Loader):

    def load_module(self, fullname):
        import tempfile
        with tempfile.NamedTemporaryFile('wb') as tmp:
            tmp.write(self.src)
            tmp.flush()
            return imp.load_compiled(fullname, tmp.name)

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
        if r is None:
            return
        if r[2][2] not in self.type_map:
            raise Exception('unknown module type')
        return self.type_map[r[2][2]](self, *r)

    type_map = {
        imp.PY_SOURCE: SrcLoader,
        imp.PY_COMPILED: PycLoader,
        imp.C_EXTENSION: ExtLoader,
        imp.PKG_DIRECTORY: PkgLoader,}

class ChannelFile(object):

    def __init__(self, channel, fid):
        self.channel, self.fid = channel, fid

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def write(self, s):
        self.channel.send(['write', self.fid, s])

    def read(self, size=-1):
        self.channel.send(['read', self.fid, size])
        return self.channel.recv()

    def seek(self, offset, whence):
        self.channel.send(['seek', self.fid, offset, whence])

    def flush(self):
        self.channel.send(['flush', self.fid])

    def close(self):
        self.channel.send(['close', self.fid])

class Remote(object):

    def __init__(self, chan):
        self.chan = chan
        self.g = dict()

    def loop(self):
        while True:
            o = self.chan.recv()
            if o[0] == 'exit': break
            if o[0] == 'result': return o[1]
            if o[0] == 'apply':
                r = eval(o[1], self.g)(*o[2:])
            elif o[0] == 'std':
                r = self.set_std(o[1], o[2])
            # elif o[0] == 'dh':
            #     r = self.do_dh(o[1], o[2])
            elif o[0] in ('exec', 'eval', 'single'):
                r = eval(compile(o[1], '<%s>' % o[0], o[0]), self.g)
            self.chan.send(['result', r])

    # def do_dh(self, other_key, other_iv):
    #     from remote import dh
    #     from Crypto.Cipher import AES

    #     # Diffie-Hellman key exchange
    #     pri_key, pri_iv = dh.gen_prikey(), dh.gen_prikey()
    #     key = dh.gen_key(pri_key, other_key)
    #     iv = dh.gen_key(pri_iv, other_iv)
    #     self.chan.send(['result', [dh.gen_pubkey(pri_key), dh.gen_pubkey(pri_iv)]])

    #     self.encryptor = AES.new(key, AES.MODE_CBC, IV=iv)
    #     self.decryptor = AES.new(key, AES.MODE_CBC, IV=iv)
    #     origwrite, origread = self.chan.write, self.chan.read
    #     def write(d):
    #         return origwrite(self.encryptor.encrypt(d))
    #     def read(n):
    #         d = origread(n)
    #         return self.decryptor.decrypt(d)
    #     self.chan.write = write
    #     self.chan.read = read

    def open(self, filepath, mode):
        self.chan.send(['open', filepath, mode])
        r = self.chan.recv()
        return ChannelFile(self, r)

    def set_std(self, which, fid):
        if which == 'stdout':
            sys.stdout = ChannelFile(self.chan, fid)
        elif which == 'stderr':
            sys.stderr = ChannelFile(self.chan, fid)

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

class BaseEncoding(object):

    def __init__(self, chan):
        self.chan = chan

    def close(self):
        self.chan.close()

class BinaryEncoding(BaseEncoding):

    def send(self, o):
        d = zlib.compress(marshal.dumps(o))
        self.chan.write(struct.pack('>I', len(d)) + d)

    def recv(self):
        l = struct.unpack('>I', self.chan.read(4))[0]
        return marshal.loads(zlib.decompress(self.chan.read(l)))

class Base64Encoding(BaseEncoding):
    
    def send(self, o):
        d = base64.b64encode(zlib.compress(marshal.dumps(o), 9))
        self.chan.write(base64.b64encode(struct.pack('>I', len(d))) + d)

    def recv(self):
        l = struct.unpack('>I', base64.b64decode(self.chan.read(8)))[0]
        o = marshal.loads(zlib.decompress(base64.b64decode(self.chan.read(l))))
        return o

class StdChannel(object):

    def __init__(self):
        self.stdin, self.stdout = sys.stdin, os.fdopen(os.dup(1), 'w')
        os.close(1)
        os.dup2(2, 1)

    def write(self, d):
        self.stdout.write(d)
        self.stdout.flush()

    def read(self, n):
        return self.stdin.read(n)

def main():
    protcls = BinaryEncoding
    if 'protocol' in Args:
        protcls = globals().get(Args['protocol'])
    channel = protcls(StdChannel())
    rmt = Remote(channel)

    sys.modules['remote.remote'] = __import__(__name__)
    sys.meta_path.append(Finder(channel))
    channel.send(['result', None])

    try:
        rmt.loop()
    except Exception as err:
        import traceback
        channel.send(['except', str(err), traceback.format_exc()])

if __name__ == '__main__': main()
