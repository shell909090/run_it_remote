#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-09-02
@author: Shell.Xu
@copyright: 2015, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
import os
import pwd
import grp
import stat
import fnmatch
import hashlib
import logging
from os import path

MAX_SYNC_SIZE = 10 * 1024 * 1024

def memorized(func):
    cache = {}
    from functools import wraps
    @wraps(func)
    def inner(k):
        if k not in cache:
            cache[k] = func(k)
        return cache[k]
    return inner

def read_file(filepath):
    with open(filepath, 'rb') as fi:
        return fi.read()

def write_file(filepath, data):
    with open(filepath, 'wb') as fo:
        fo.write(data)

def read_files(fs):
    return [read_file(f) for f in fs]

def write_files(fs):
    for f, d in fs:
        write_file(f, d)

@memorized
def get_username(uid):
    return pwd.getpwuid(uid).pw_name

@memorized
def get_userid(username):
    return pwd.getpwnam(username).pw_uid

@memorized
def get_groupname(gid):
    return grp.getgrgid(gid).gr_name

@memorized
def get_groupid(groupname):
    return grp.getgrnam(groupname).gr_gid

def gen_md5hash(filepath):
    try:
        h = hashlib.md5()
        h.update(read_file(filepath))
        return h.hexdigest()
    except IOError: # no priv to read
        return

def gen_fileinfo(filepath, start=None):
    filepath = path.abspath(filepath)
    rpath = filepath
    if start is not None:
        rpath = path.relpath(filepath, start)
    st = os.lstat(filepath)
    if stat.S_IFMT(st.st_mode) not in (stat.S_IFREG, stat.S_IFLNK, stat.S_IFDIR):
        return
    fi = {
        'path': rpath,
        'type': stat.S_IFMT(st.st_mode), 'mode': stat.S_IMODE(st.st_mode),
        'user': get_username(st.st_uid), 'group': get_groupname(st.st_gid)}

    if stat.S_ISREG(st.st_mode):
        fi['md5'] = gen_md5hash(filepath)
        fi['size'] = st.st_size
    elif stat.S_ISLNK(st.st_mode):
        fi['link'] = os.readlink(filepath)
    return fi

def walkdir(basedir, start=None, partten=None):
    basedir = path.abspath(basedir)
    filist = [gen_fileinfo(basedir, start)]
    for root, dirs, files in os.walk(basedir):
        for filename in files + dirs:
            filepath = path.join(root, filename)
            if partten:
                rpath = path.relpath(filepath, root)
                if not fnmatch.fnmatch(rpath, partten):
                    continue
            fi = gen_fileinfo(filepath, start)
            if 'size' in fi and fi['size'] > MAX_SYNC_SIZE:
                logging.error('file %s size %d out of limit', filepath, fi['size'])
                continue # pass
            if fi: filist.append(fi)
    return filist
