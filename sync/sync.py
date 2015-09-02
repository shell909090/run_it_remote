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

# CAUTION: the owner and privilege of the sync dir it own will not to write in any .meta file.
# this may cause sync dir's owner change or mode change.

# TODO: sync file to.

# TODO: sync files back, use write files. process multiple files in one call.
def sync_file_back(ins, remote, local, desc):
    if path.exists(local):
        st = os.stat(local)
        if not stat.S_ISREG(st.st_mode):
            raise Exception('remote file to local non-file %s' % local)
        if st.st_size == desc['size'] and api.gen_md5hash(local) == desc['md5']:
            return # done
    if desc['size'] > MAX_SYNC_SIZE:
        raise Exception('file %s size %d out of limit' % (remote, fi[0]))
    # if base dir not exist, create it first.
    dirname = path.dirname(local)
    if not path.exists(dirname):
        os.makedirs(dirname)
    # where did I get metafile?
    # so desc can't just write a file.
    # if so, no meta file.
    data = ins.apply(api.read_file, remote)
    with open(local, 'wb') as fi:
        fi.write(data)

def write_down_meta(filepath, desc):
    newdesc = {'common': desc['common']}
    newdesc['dirlist'] = dict([
        (k, v) for k, v in desc['dirlist'].iteritems() if v])
    filelist = {}
    for file, d in desc['filelist'].iteritems():
        dn = dict([(k, v) for k, v in d.items() if k in ('user', 'group', 'mode')])
        if dn: filelist[file] = dn
    newdesc['filelist'] = filelist
    with open(filepath, 'wb') as fo:
        fo.write(yaml.dump(newdesc))

def sync_back(ins, remote, local, recurse=True, partten=None):
    logging.warning('sync %s in %s.' % (remote, str(ins)))
    desc = ins.apply(api.gen_desc, remote, partten)

    # this is a file.
    if 'common' not in desc:
        sync_file_back(ins, remote, local, desc)
        return

    # it must be a dir now.
    # if local dir not exists, create it first.
    if not path.exists(local):
        os.makedirs(local)
    # sync all files back
    for file, d in desc['filelist'].iteritems():
        if partten and not fnmatch.fnmatch(file, partten):
            continue
        sync_file_back(ins, path.join(remote, file), path.join(local, file), d)
    # write down meta file
    write_down_meta(path.join(local, '.meta'), desc)
    # if recurse, sync dir recursively.
    if not recurse: return
    for dir, d in desc['dirlist'].iteritems():
        if partten and not fnmatch.fnmatch(file, partten):
            continue
        sync_back(ins, path.join(remote, dir), path.join(local, dir), recurse, None)
