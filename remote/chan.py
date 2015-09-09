#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-09-09
@author: Shell.Xu
@copyright: 2015, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
import subprocess

class ProcessChannel(object):

    def __init__(self, cmd):
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

    def __init__(self, bootstrap):
        ProcessChannel.__init__(self, ['python', '-c', bootstrap])

    def __repr__(self):
        return '<local>'

class SshChannel(ProcessChannel):

    def __init__(self, bootstrap, host):
        ProcessChannel.__init__(self, ['ssh', host, 'python', '-c', '"%s"' % bootstrap])
        self.host = host

    def __repr__(self):
        return self.host

class SshSudoChannel(ProcessChannel):

    def __init__(self, bootstrap, host, user=None):
        if user:
            cmd = ['ssh', host, 'sudo', '-u', user,
                   'python', '-c', '"%s"' % bootstrap]
        else:
            cmd = ['ssh', host, 'sudo',
                   'python', '-c', '"%s"' % bootstrap]
        ProcessChannel.__init__(self, cmd)
        self.host, self.user = host, user

    def __repr__(self):
        return self.host

class ParamikoChannel(object):

    # had to set auto_hostkey to True
    # for detail: https://github.com/paramiko/paramiko/issues/67
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

    def __init__(self, bootstrap, host, auto_hostkey=False, **kw):
        cmd = 'python -c "%s"' % bootstrap
        ParamikoChannel.__init__(self, host, cmd, auto_hostkey, **kw)
        self.host = host

    def __repr__(self):
        return self.host

class PSshSudoChannel(ParamikoChannel):

    def __init__(self, bootstrap, host, user=None, auto_hostkey=False, **kw):
        if user:
            cmd = 'sudo -u %s python -c "%s"' % (user, bootstrap)
        else:
            cmd = 'sudo python -c "%s"' % bootstrap
        ParamikoChannel.__init__(self, host, cmd, auto_hostkey, **kw)
        self.host, self.user = host, user

    def __repr__(self):
        return self.host
