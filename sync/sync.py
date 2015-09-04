#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-09-02
@author: Shell.Xu
@copyright: 2015, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
import os
import stat
import fnmatch
import logging
from os import path
import yaml
import api

MAX_SYNC_SIZE = 10 * 1024 * 1024

# TODO: sync file to.

def reloca_path(filepath, origbase, newbase):
    rpath = path.relpath(filepath, origbase)
    if rpath == '.': return newbase
    return path.join(newbase, rpath)

def chk4file(filist, remote, local):
    f2sync = []
    for fi in filist:
        if fi['type'] != stat.S_IFREG: continue
        localpath = reloca_path(fi['path'], remote, local)
        print fi['path'], remote, local, '=>', localpath

        if fi['size'] > MAX_SYNC_SIZE:
            logging.error('file %s size %d out of limit' % (localpath, fi['size']))
            continue # pass

        if path.lexists(localpath): # link is not ok.
            st = os.lstat(localpath)
            if not stat.S_ISREG(st.st_mode):
                logging.error('remote file to local non-file %s' % local)
                continue
            if st.st_size == fi['size'] and api.gen_md5hash(localpath) == fi['md5']:
                continue # done

        # if base dir not exist, create it first.
        dirname = path.dirname(localpath)
        if not path.exists(dirname): # link is ok.
            print 'create dir', dirname
            logging.info('create dir %s' % dirname)
            os.makedirs(dirname)

        f2sync.append((fi['path'], localpath))
    return f2sync

def sync_back(rmt, remote, local, partten=None):
    logging.warning('sync %s in %s to %s.' % (remote, str(rmt), local))
    filist = rmt.apply(api.walkdir, remote, None, partten)
    f2sync = chk4file(filist, remote, local)
    try:
        datas = rmt.apply(api.read_files, [f[0] for f in f2sync])
        api.write_files(zip([f[1] for f in f2sync], datas))
    except: # read_files failed, maybe total size of files are larger then 4GB.
        for rmtpath, localpath in f2sync:
            data = rmt.apply(api.read_file, rmtpath)
            api.write_file(localpath, data)
    return filist

def sync_to(rmt, remote, local, partten=None):
    logging.warning('sync %s to %s in %s' % (local, remote, str(rmt)))
    filist = api.walkdir(local, os.getcwd(), partten)
    f2sync = rmt.apply(chk4file, filist, local, remote)
    try:
        datas = api.read_files([f[0] for f in f2sync])
        rmt.apply(api.write_files, zip([f[1] for f in f2sync], datas))
    except:
        for localpath, rmtpath in f2sync:
            data = api.read_file(localpath)
            rmt.apply(api.write_file, data)
    return filist
