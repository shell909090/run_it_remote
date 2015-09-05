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
    if o is None:
        logging.debug('%s: none', action)
    elif isinstance(o, list):
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

    def get_args(self):
        return {'protocol': 'Base64Encoding'}

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
            d = self.p.stdout.read(n)
            if not d: raise EOFError()
            return d
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

class ParamikoChannel(object):

    # had to set auto_hostkey to True, for detail: https://github.com/paramiko/paramiko/issues/67

    def __init__(self, host, cmd, auto_hostkey=True, **kw):
        import paramiko
        self.ssh = paramiko.SSHClient()
        print self.ssh.get_host_keys().items()
        self.ssh.load_system_host_keys()
        print self.ssh.get_host_keys().items()
        if auto_hostkey:
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(host, **kw)
        self.stdin, self.stdout, self.stderr = self.ssh.exec_command(cmd)

    def close(self):
        self.ssh.close()

    def write(self, d):
        try:
            self.stdin.write(d)
            self.stdin.flush()
        except:
            print self.stderr.read()
            raise

    def read(self, n):
        try:
            return self.stdout.read(n)
        except:
            print self.stderr.read()
            raise

class PSshChannel(ParamikoChannel):

    def __init__(self, host, auto_hostkey=False, **kw):
        cmd = 'python -c "%s"' % self.BOOTSTRAP
        ParamikoChannel.__init__(self, host, cmd, auto_hostkey, **kw)
        self.host = host

    def __repr__(self):
        return self.host

class PSshSudoChannel(ParamikoChannel):

    def __init__(self, host, user=None, auto_hostkey=False, **kw):
        if user:
            cmd = 'sudo -u %s python -c "%s"' % (user, self.BOOTSTRAP)
        else:
            cmd = 'sudo python -c "%s"' % self.BOOTSTRAP
        ParamikoChannel.__init__(self, host, cmd, auto_hostkey, **kw)
        self.host, self.user = host, user

    def __repr__(self):
        return self.host

class Remote(object):

    def __init__(self, chan, args=None):
        self.chan = chan
        self.g = {}
        self.fmaps = {}
        self.mc = set()
        self.args = args if args is not None else {}
        self.send_remote_core()

    def send_remote_core(self):
        kw = self.args.copy()
        if hasattr(self.chan, 'get_args'):
            kw.update(self.chan.get_args())

        basedir = path.dirname(__file__)
        with open(path.join(basedir, 'remote.py'), 'r') as fi:
            d = fi.read()
        d = d.replace('None # replace Parameter here.', str(kw))

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

    def enable_aes(self):
        import dh
        from Crypto.Cipher import AES

        # Diffie-Hellman key exchange
        pri_key, pri_iv = dh.gen_prikey(), dh.gen_prikey()
        self.chan.send(['dh', dh.gen_pubkey(pri_key), dh.gen_pubkey(pri_iv)])
        other_key, other_iv = self.loop()
        key = dh.gen_key(pri_key, other_key)
        iv = dh.gen_key(pri_iv, other_iv)

        self.encryptor = AES.new(key, AES.MODE_CBC, IV=iv)
        self.decryptor = AES.new(key, AES.MODE_CBC, IV=iv)
        origwrite, origread = self.chan.write, self.chan.read
        def write(d):
            return origwrite(self.encryptor.encrypt(d))
        def read(n):
            d = origread(n)
            return self.decryptor.decrypt(d)
        self.chan.write = write
        self.chan.read = read

        # for last result.
        return self.loop()

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
            self.import_module(m.__name__)
            fname = m.__name__ + '.' + fname
        return fname

    def import_module(self, name):
        if name in self.mc: return
        self.execute('import ' + name)
        self.mc.add(name)
