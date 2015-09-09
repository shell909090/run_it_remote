#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-09-09
@author: Shell.Xu
@copyright: 2015, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
import stat
import collections

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
    common['filemode'] = int(common['filemode'], 8)
    common['dirmode'] = int(common['dirmode'], 8)

    for filepath, fi in doc['filelist'].iteritems():
        fi['path'] = filepath
        fi['type'] = reversed_map(filetype_map, fi['type'])
        if 'mode' in fi:
            fi['mode'] = int(fi['mode'], 8)
    return doc
