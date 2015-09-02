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
import collections
from os import path

def read_file(filepath):
    with open(filepath, 'rb') as fi:
        return fi.read()

def write_file(filepath, data):
    with open(filepath, 'wb') as fo:
        fo.write(data)

def read_files(*fs):
    return [read_file(f) for f in fs]

def write_files(*fs):
    for f, d in fs:
        write_file(f, d)

def get_username(uid):
    return pwd.getpwuid(uid).pw_name

def get_groupname(gid):
    return grp.getgrgid(gid).gr_name

def gen_fileinfo(filepath):
    st = os.lstat(filepath)
    return [path.basename(filepath), st.st_size, st.st_mode,
            get_username(st.st_uid), get_groupname(st.st_gid)]

def listdir(dirname, partten=None):
    filist = []
    for filename in os.listdir(dirname):
        if partten and not fnmatch.fnmatch(filename, partten):
            continue
        fi = gen_fileinfo(path.join(dirname, filename))
        if stat.S_IFMT(fi[2]) in (stat.S_IFREG, stat.S_IFDIR):
            filist.append(fi)
    return filist

def stat_dir(filist):
    users = collections.Counter()
    groups = collections.Counter()
    files = collections.Counter()
    dirs = collections.Counter()
    for fi in filist:
        users[fi[3]] += 1
        groups[fi[4]] += 1
        st = fi[2]
        if stat.S_ISREG(st):
            files[stat.S_IMODE(st)] += 1
        elif stat.S_ISDIR(st):
            dirs[stat.S_IMODE(st)] += 1
    return (
        users.most_common(1)[0][0] if users else None,
        groups.most_common(1)[0][0] if groups else None,
        files.most_common(1)[0][0] if files else None,
        dirs.most_common(1)[0][0] if dirs else None)

def gen_md5hash(filepath):
    try:
        h = hashlib.md5()
        h.update(read_file(filepath))
        return h.hexdigest()
    except IOError:
        return

def gen_file_desc(filepath, username=None, groupname=None, filemode=None):
    fi = gen_fileinfo(filepath)
    fstat = {'size': fi[1]}
    md5 = gen_md5hash(filepath)
    if md5:
        fstat['md5'] = md5
    if fi[3] != username:
        fstat['user'] = fi[3]
    if fi[4] != groupname:
        fstat['group'] = fi[4]
    if stat.S_IMODE(fi[2]) != filemode:
        fstat['mode'] = stat.S_IMODE(fi[2])
    return fstat

# TODO: record lnk in meta file
def gen_dir_desc(dirname, partten=None):
    filist = listdir(dirname, partten)
    username, groupname, filemode, dirmode = stat_dir(filist)
    files, dirs = {}, {}
    for fi in filist:
        st = fi[2]
        if stat.S_ISREG(st):
            files[fi[0]] = gen_file_desc(
                path.join(dirname, fi[0]), username, groupname, filemode)
        elif stat.S_ISDIR(st):
            fstat = {}
            if stat.S_IMODE(st) != dirmode:
                fstat['mode'] = st
            dirs[fi[0]] = fstat
    return {
        'common': {
            'username': username,
            'groupname': groupname,
            'filemode': filemode,
            'dirmode': dirmode},
        'dirlist': dirs,
        'filelist': files}

def gen_desc(filepath, partten=None):
    st = os.stat(filepath)
    if stat.S_ISREG(st.st_mode):
        return gen_file_desc(filepath)
    elif stat.S_ISDIR(st.st_mode):
        return gen_dir_desc(filepath, partten)
