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
                logging.error('file %s size %d out of limit' % (localpath, fi['size']))
                continue # pass
            if fi: filist.append(fi)
    return filist

def listdir(dirname, partten=None):
    filist = []
    for filename in os.listdir(dirname):
        if partten and not fnmatch.fnmatch(filename, partten):
            continue
        fi = gen_fileinfo(path.join(dirname, filename))
        if fi:
            filist.append(fi)
    return filist

def stat_dir_user(filist, username=None):
    if username: return username
    users = collections.Counter()
    for fi in filist:
        users[fi['user']] += 1
    return users.most_common(1)[0][0] if users else None

def stat_dir_group(filist, groupname=None):
    if groupname: return groupname
    groups = collections.Counter()
    for fi in filist:
        groups[fi['group']] += 1
    return groups.most_common(1)[0][0] if groups else None

def stat_dir_mode(filist, filemode=None, dirmode=None):
    if filemode and dirmode: return filemode, dirmode
    files = collections.Counter()
    dirs = collections.Counter()
    for fi in filist:
        st = fi['type']
        if stat.S_ISREG(st) or stat.S_ISLNK(st):
            files[fi['mode']] += 1
        elif stat.S_ISDIR(st):
            dirs[fi['mode']] += 1
    if not filemode:
        filemode = files.most_common(1)[0][0] if files else None
    if not dirmode:
        dirmode = dirs.most_common(1)[0][0] if dirs else None
    return filemode, dirmode

def limit_attr(fi, attrs):
    rslt = {}
    for k, v in fi.iteritems():
        if k in attrs:
            rslt[k] = v
    return rslt

filetype_map = {
    stat.S_IFDIR: 'dir',
    stat.S_IFREG: 'file',
    stat.S_IFLNK: 'link',
}

def reversed_map(m, v1):
    for k, v in m.iteritems():
        if v == v1:
            return k

def transmode(fi, value):
    if fi['mode'] == value:
        del fi['mode']
    else:
        fi['mode'] = oct(fi['mode'])

def filist_dump(filist, username=None, groupname=None, filemode=None, dirmode=None):
    username = stat_dir_user(filist, username)
    groupname = stat_dir_group(filist, groupname)
    filemode, dirmode = stat_dir_mode(filist, filemode, dirmode)
    fileattrs = set(['path', 'type',])

    files = {}
    for fi in filist:
        if 'md5' in fi: del fi['md5']
        if 'size' in fi: del fi['size']

        if fi['user'] == username: del fi['user']
        if fi['group'] == groupname: del fi['group']

        if fi['type'] in (stat.S_IFREG, stat.S_IFLNK):
            transmode(fi, filemode)
        elif fi['type'] == stat.S_IFDIR:
            transmode(fi, dirmode)
        else:
            raise Exception('unknown file type %s' % oct(fi['type']))
        if set(fi.keys()) == fileattrs: continue

        fi['type'] = filetype_map[fi['type']]
        files[fi['path']] = fi
        del fi['path']

    import yaml
    return yaml.dump({
        'common': {
            'username': username,
            'groupname': groupname,
            'filemode': oct(filemode),
            'dirmode': oct(dirmode)},
        'filelist': files})

def filist_load(doc):
    import yaml
    doc = yaml.load(doc)
    common = doc['common']
    username, groupname = common['username'], common['groupname']
    common['filemode'] = int(common['filemode'], 8)
    common['dirmode'] = int(common['dirmode'], 8)

    for filepath, fi in doc['filelist'].iteritems():
        fi['path'] = filepath
        fi['type'] = reversed_map(filetype_map, fi['type'])
        if 'mode' in fi:
            fi['mode'] = int(fi['mode'], 8)
    return doc
