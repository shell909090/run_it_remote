#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-09-09
@author: Shell.Xu
@copyright: 2015, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
import zlib
import base64
import struct
import marshal
import logging

def show_msg(action, o):
    if o is None:
        logging.debug('%s: none', action)
        return
    if isinstance(o, (int, long)):
        logging.debug('%s int: %d', action, o)
        return
    if isinstance(o, list):
        d = str(o)
    elif isinstance(o, basestring):
        d = o
    else:
        logging.debug('%s: unknown', action)
        return
    if len(d) >= 200:
        logging.debug('%s: too long', action)
        return
    logging.debug('%s: %s', action, d)

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

    @staticmethod
    def get_args():
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

    BOOTSTRAP = ''

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
