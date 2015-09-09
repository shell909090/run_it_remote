#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-08-14
@author: shell.xu
@copyright: 2015, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
import sys
import imp
import inspect
import logging
from os import path

def remote_initlog(loglevel, fmt):
    rootlog = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, '%H:%M:%S'))
    rootlog.addHandler(handler)
    if loglevel:
        rootlog.setLevel(loglevel)

class Remote(object):

    def __init__(self, chancls, protcls, host,
                 args=None, chankw=None, protkw=None):
        self.g = {}
        self.fmaps = {}
        self.mc = set()
        self.args = args if args is not None else {}

        if chankw is None: chankw = {}
        chan = chancls(protcls.BOOTSTRAP, host, **chankw)
        if protkw is None: protkw = {}
        self.chan = protcls(chan, **protkw)
        self.send_remote_core()
        self.monkeypatch_std('stdout')

    def send_remote_core(self):
        kw = self.args.copy()
        if hasattr(self.chan, 'get_args'):
            kw.update(self.chan.get_args())

        basedir = path.dirname(__file__)
        with open(path.join(basedir, 'remote.py'), 'r') as fi:
            d = fi.read()
        logging.debug('kw: %s', str(kw))
        d = d.replace('{} # replace Parameter here.', str(kw))

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
                getattr(self, '_on_' + o[0])(*o[1:])

    def _on_open(self, filepath, mode):
        f = open(filepath, mode)
        self.fmaps[id(f)] = f
        self.chan.send(id(f))

    def _on_std(self, which):
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

    def _on_write(self, fid, d):
        self.fmaps[fid].write(d)

    def _on_read(self, fid, size):
        d = self.fmaps[fid].read(size)
        self.chan.send(d)

    def _on_seek(self, fid, offset, whence):
        self.fmaps[fid].seek(offset, whence)

    def _on_flush(self, fid):
        self.fmaps[fid].flush()

    def _on_close(self, fid):
        f = self.fmaps[fid]
        if f not in (sys.stdin, sys.stdout, sys.stderr):
            f.close()
        del self.fmaps[fid]

    def _on_find_module(self, name, findpath):
        try:
            r = list(imp.find_module(name, findpath))
            if r[0] is not None:
                with r[0]:
                    d = r[0].read()
                r[0] = d
            self.chan.send(r)
        except ImportError: self.chan.send(None)

    def _on_except(self, err, exc):
        logging.error(''.join(exc))
        raise Exception(err)

    # def enable_aes(self):
    #     from remote import dh
    #     from Crypto.Cipher import AES

    #     # Diffie-Hellman key exchange
    #     pri_key, pri_iv = dh.gen_prikey(), dh.gen_prikey()
    #     self.chan.send(['dh', dh.gen_pubkey(pri_key), dh.gen_pubkey(pri_iv)])
    #     other_key, other_iv = self.loop()
    #     key = dh.gen_key(pri_key, other_key)
    #     iv = dh.gen_key(pri_iv, other_iv)

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

    #     # for last result.
    #     return self.loop()

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

    def monkeypatch_std(self, which):
        if which == 'stdout':
            f = sys.stdout
        elif which == 'stderr':
            f = sys.stderr
        else:
            raise Exception('unknown std: %s' % which)
        self.fmaps[id(f)] = f
        self.chan.send(['std', which, id(f)])
        return self.loop()

    LOG_FMT = '%(asctime)s,%(msecs)03d [%(levelname)s] <remote,%(name)s>: %(message)s'
    def monkeypatch_logging(self, loglevel='INFO', fmt=None):
        if not fmt: fmt = self.LOG_FMT
        self.apply(remote_initlog, loglevel.upper(), fmt)
