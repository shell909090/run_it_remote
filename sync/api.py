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

def read_files(fs):
    return [read_file(f) for f in fs]

def write_files(fs):
    for f, d in fs:
        write_file(f, d)

def get_username(uid):
    return pwd.getpwuid(uid).pw_name

def get_groupname(gid):
    return grp.getgrgid(gid).gr_name


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
            if fi:
                filist.append(fi)
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

def stat_dir(filist):
    users = collections.Counter()
    groups = collections.Counter()
    files = collections.Counter()
    dirs = collections.Counter()
    for fi in filist:
        users[fi['user']] += 1
        groups[fi['group']] += 1
        st = fi['type']
        if stat.S_ISREG(st) or stat.S_ISLNK(st):
            files[fi['mode']] += 1
        elif stat.S_ISDIR(st):
            dirs[fi['mode']] += 1
    return (
        users.most_common(1)[0][0] if users else None,
        groups.most_common(1)[0][0] if groups else None,
        files.most_common(1)[0][0] if files else None,
        dirs.most_common(1)[0][0] if dirs else None)

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

# FIXME: setable username, groupname, filemode, dirmode
def filist_dump(filist):
    username, groupname, filemode, dirmode = stat_dir(filist)
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
    filemode, dirmode = int(common['filemode'], 8), int(common['dirmode'], 8)

    for filepath, fi in doc['filelist'].iteritems():
        fi['path'] = filepath
        if 'user' not in fi: fi['user'] = username
        if 'group' not in fi: fi['group'] = groupname
        fi['type'] = reversed_map(filetype_map, fi['type'])

        if 'mode' not in fi:
            if fi['type'] in (stat.S_IFREG, stat.S_IFLNK):
                fi['mode'] = filemode
            elif fi['type'] == stat.S_IFDIR:
                fi['mode'] = dirmode
        else:
            fi['mode'] = int(fi['mode'], 8)
        yield fi

# TODO: record lnk in meta file
def gen_dir_desc(dirname, partten=None):
    filist = listdir(dirname, partten)
    username, groupname, filemode, dirmode = stat_dir(filist)
    files, dirs = {}, {}
    for fi in filist:
        st = fi[2]
        if stat.S_ISREG(st) or stat.S_ISLNK(st):
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
