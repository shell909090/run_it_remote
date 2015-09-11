#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-09-11
@author: Shell.Xu
@copyright: 2015, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
import sys, imp

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

import run_it_remote
sys.meta_path.append(Finder(run_it_remote.channel))
