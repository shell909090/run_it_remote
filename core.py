import os, sys, imp, zlib, StringIO, tempfile

stdout = os.fdopen(os.dup(1), 'w')
os.close(1)
os.dup2(2, 1)

def write(o):
    marshal.dump(o, stdout)
    stdout.flush()

class StdPipe(object):
    def write(self, s): write(['otpt', s])
    def flush(self): write(['flsh', s])
sys.stdout = StdPipe()

def add_module(name):
    if name not in sys.modules:
        sys.modules[name] = imp.new_module(name)
    return sys.modules[name]

class Loader(object):
    def __init__(self, src, pathname, description):
        self.src, self.pathname, self.description = src, pathname, description
    def exec_code_module(self, mod):
        co = compile(zlib.decompress(self.src), self.pathname, 'exec')
        exec co in mod.__dict__

class SrcLoader(Loader):
    def load_module(self, fullname):
        mod = add_module(fullname)
        mod.__file__ = self.pathname
        self.exec_code_module(mod)
        return mod

class ExtLoader(Loader):
    def load_module(self, fullname):
        with tempfile.NamedTemporaryFile('wb') as tmp:
            tmp.write(zlib.decompress(self.src))
            tmp.flush()
            imp.load_dynamic(fullname, tmp.name)
        return mod

class PkgLoader(Loader):
    def load_module(self, fullname):
        loader = finder.find_remote('__init__', [self.pathname,])
        mod = add_module(fullname)
        mod.__file__ = loader.pathname
        mod.__path__ = [self.pathname,]
        mod.__package__ = fullname
        loader.exec_code_module(mod)
        return mod

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
        r = marshal.load(sys.stdin)
        if r is not None: return self.type_map[r[2][2]](*r)
    type_map = {
        imp.PY_SOURCE: SrcLoader,
        imp.C_EXTENSION: ExtLoader,
        imp.PKG_DIRECTORY: PkgLoader}

finder = Finder()
sys.meta_path.append(finder)

glb = dict()
while True:
    o = marshal.load(sys.stdin)
    if o[0] == 'exit': break
    if o[0] == 'exec': co = compile(o[1], '<exec>', 'exec')
    elif o[0] == 'eval': co = compile(o[1], '<eval>', 'eval')
    write(['rslt', eval(co, glb)])
