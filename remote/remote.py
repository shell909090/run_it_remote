#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
@date: 2015-08-14
@author: shell.xu
@copyright: 2015, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
import os, sys, zlib, struct, marshal, logging, base64
import importlib.util
import importlib.machinery
import tempfile
import traceback

Args = None # replace Parameter here.

class Loader:
    def __init__(self, origin, locations, kind, data):
        self.origin, self.locations, self.kind, self.data = origin, locations, kind, data

    def create_module(self, spec):
        if self.kind == 'extension':
            self.temp = tempfile.TemporaryDirectory()
            filename = os.path.join(self.temp.name, os.path.basename(self.origin))
            with open(filename, 'wb') as output: output.write(self.data)
            self.native = importlib.machinery.ExtensionFileLoader(spec.name, filename)
            native_spec = importlib.util.spec_from_file_location(spec.name, filename, loader=self.native)
            return self.native.create_module(native_spec)
        return None

    def exec_module(self, module):
        module.__file__ = self.origin
        if self.kind == 'extension':
            self.native.exec_module(module)
        else:
            code = marshal.loads(self.data[16:]) if self.kind == 'bytecode' else compile(self.data, self.origin, 'exec')
            exec(code, module.__dict__)

class Finder:
    def __init__(self, channel): self.channel = channel

    def find_spec(self, fullname, path=None, target=None):
        self.channel.send(['find_module', fullname, path])
        result = self.channel.recv()
        if result is None: return None
        loader = Loader(*result)
        spec = importlib.util.spec_from_loader(fullname, loader, is_package=bool(loader.locations))
        if loader.locations: spec.submodule_search_locations = loader.locations
        return spec

class ChannelFile(object):

    def __init__(self, channel, id):
        self.channel, self.id = channel, id

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def write(self, s):
        self.channel.send(['write', self.id, s])

    def read(self, size=-1):
        self.channel.send(['read', self.id, size])
        return self.channel.recv()

    def seek(self, offset, whence):
        self.channel.send(['seek', self.id, offset, whence])

    def flush(self):
        self.channel.send(['flush', self.id])

    def close(self):
        self.channel.send(['close', self.id])

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
            elif o[0] == 'dh':
                r = self.do_dh(o[1], o[2])
            elif o[0] in ('exec', 'eval', 'single'):
                r = eval(compile(o[1], '<%s>' % o[0], o[0]), self.g)
            self.chan.send(['result', r])

    def do_dh(self, other_key, other_iv):
        from remote import dh
        from Crypto.Cipher import AES

        # Diffie-Hellman key exchange
        pri_key, pri_iv = dh.gen_prikey(), dh.gen_prikey()
        key = dh.gen_key(pri_key, other_key)
        iv = dh.gen_key(pri_iv, other_iv)[:16]
        self.chan.send(['result', [dh.gen_pubkey(pri_key), dh.gen_pubkey(pri_iv)]])

        self.encryptor = AES.new(key, AES.MODE_CFB, iv=iv, segment_size=128)
        self.decryptor = AES.new(key, AES.MODE_CFB, iv=iv, segment_size=128)
        origwrite, origread = self.chan.write, self.chan.read
        def write(d):
            return origwrite(self.encryptor.encrypt(d))
        def read(n):
            d = origread(n)
            return self.decryptor.decrypt(d)
        self.chan.write = write
        self.chan.read = read

    def open(self, filepath, mode):
        self.chan.send(['open', filepath, mode])
        r = self.chan.recv()
        return ChannelFile(self.chan, r)

    def getstd(self, which):
        self.chan.send(['std', which])
        id = self.chan.recv()
        return ChannelFile(self.chan, id)

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

class BinaryEncoding(object):

    def send(self, o):
        d = zlib.compress(marshal.dumps(o))
        self.write(struct.pack('>I', len(d)) + d)

    def recv(self):
        l = struct.unpack('>I', self.read(4))[0]
        return marshal.loads(zlib.decompress(self.read(l)))

class Base64Encoding(object):
    
    def send(self, o):
        d = base64.b64encode(zlib.compress(marshal.dumps(o), 9))
        self.write(base64.b64encode(struct.pack('>I', len(d))) + d)

    def recv(self):
        l = struct.unpack('>I', base64.b64decode(self.read(8)))[0]
        o = marshal.loads(zlib.decompress(base64.b64decode(self.read(l))))
        return o

class StdChannel(object):

    def __init__(self):
        self.stdin, self.stdout = sys.stdin.buffer, os.fdopen(os.dup(1), 'wb')
        os.close(1)
        os.dup2(2, 1)

    def write(self, d):
        self.stdout.write(d)
        self.stdout.flush()

    def read(self, n):
        return self.stdin.read(n)

def initlog():
    rootlog = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            '%(asctime)s,%(msecs)03d [%(levelname)s] <remote,%(name)s>: %(message)s',
            '%H:%M:%S'))
    rootlog.addHandler(handler)
    if 'loglevel' in Args:
        rootlog.setLevel(Args['loglevel'])

def main():
    protocol = BinaryEncoding
    if 'protocol' in Args:
        protocol = globals().get(Args['protocol'])
    channel = type('C', (StdChannel, protocol), {})()
    remote = Remote(channel)
    globals()["channel"] = remote

    sys.modules['remote.remote'] = __import__(__name__)
    sys.meta_path.append(Finder(channel))
    sys.stdout = remote.getstd('stdout')
    initlog()
    channel.send(['result', None])

    remote.loop()

if __name__ == '__main__': main()
