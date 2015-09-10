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
import logging
from os import path
import remote
import api
import __main__
import metafile

def reloca_path(filepath, origbase, newbase):
    rpath = path.relpath(filepath, origbase)
    if rpath == '.':
        reloc = newbase
    else:
        reloc = path.join(newbase, rpath)
    logging.debug('%s reloc from %s to %s => %s',
                  filepath, origbase, newbase, reloc)
    return reloc

def sync_dir(filist, rmtbase, localbase):
    for fi in filist:
        if fi['type'] != stat.S_IFDIR: continue
        localpath = reloca_path(fi['path'], rmtbase, localbase)

        if path.lexists(localpath):
            if not path.isdir(localpath):
                logging.error('remote dir to local non-dir %s', localpath)
                continue
        else:
            os.makedirs(localpath)

def chk4file(localpath, fi):
    st = os.lstat(localpath)
    if not stat.S_ISREG(st.st_mode):
        logging.error('remote file to local non-file %s', localpath)
        return True
    if st.st_size == fi['size'] and api.gen_md5hash(localpath) == fi['md5']:
        return True # done

def chk4dir(dirname):
    if path.exists(dirname): # link is ok.
        return
    logging.info('create dir %s', dirname)
    os.makedirs(dirname)

def chk4files(filist, rmtbase, localbase):
    f2sync = []
    for fi in filist:
        if fi['type'] != stat.S_IFREG: continue
        localpath = reloca_path(fi['path'], rmtbase, localbase)

        if path.lexists(localpath): # link is not ok.
            if chk4file(localpath, fi):
                continue

        # if base dir not exist, create it first.
        chk4dir(path.dirname(localpath))

        f2sync.append((fi['path'], localpath))
    return f2sync

def sync_files_back(rmt, f2sync, filist):
    if not f2sync: return
    try:
        datas = rmt.apply(api.read_files, [f[0] for f in f2sync])
        api.write_files(zip([f[1] for f in f2sync], datas))
    except Exception as err:
        # maybe total size of files are larger then 4GB.
        logging.error("sync files failed, exception: %s.", str(err))
        logging.info("retry sync file one by one.")
        for rmtpath, localpath in f2sync:
            data = rmt.apply(api.read_file, rmtpath)
            api.write_file(localpath, data)

def sync_files_to(rmt, f2sync, filist):
    if not f2sync: return
    try:
        datas = api.read_files([f[0] for f in f2sync])
        rmt.apply(api.write_files, zip([f[1] for f in f2sync], datas))
    except Exception as err:
        # maybe total size of files are larger then 4GB.
        logging.error("sync files failed, exception: %s", str(err))
        logging.info("retry sync file one by one.")
        for localpath, rmtpath in f2sync:
            data = api.read_file(localpath)
            rmt.apply(api.write_file, rmtpath, data)

def get_syncinfo(rmt, desc, syncinfo):
    rmtpath = syncinfo['remote']
    if rmtpath.startswith('~'):
        rmtpath = rmt.apply(path.expanduser, rmtpath)

    partten = None
    if '*' in rmtpath:
        partten, rmtpath = path.basename(rmtpath), path.dirname(rmtpath)
        logging.info('rmt: %s, partten: %s', rmtpath, partten)
        if '*' in rmtpath:
            raise Exception('match just allow in last level.')

    local = syncinfo.get('local') or rmtpath
    if local.startswith(path.sep):
        local = local[1:]
    local = path.join(desc['hostname'], local)
    return rmtpath, local, partten

def cache_default_attr(attrs):
    common = attrs['common']
    attrs['file'] = {
        'user': common['username'],
        'group': common['groupname'],
        'mode': common['filemode']}
    attrs['dir'] = {
        'user': common['username'],
        'group': common['groupname'],
        'mode': common['dirmode']}

def limit_attr(fi, attrs):
    rslt = {}
    for k, v in fi.iteritems():
        if k in attrs:
            rslt[k] = v
    return rslt

def merge_filist(filist, attrs, rmtbase, localbase):
    attrfiles = attrs['filelist']

    for rmtpath, fi in attrfiles.items():
        fi['path'] = rmtpath
        if fi['type'] != stat.S_IFLNK:
            continue
        fi = limit_attr(fi, set(['user', 'group', 'path', 'mode', 'type', 'link']))
        fi2 = attrs['file'].copy()
        fi2.update(fi)
        yield fi2

    for fi in filist:
        fi2 = limit_attr(fi, set(['user', 'group', 'path', 'mode', 'type']))

        if fi['type'] == stat.S_IFREG:
            fi2.update(attrs['file'])
        elif fi['type'] == stat.S_IFDIR:
            fi2.update(attrs['dir'])

        rmtpath = reloca_path(fi['path'], localbase, rmtbase)
        fi2['path'] = rmtpath
        if rmtpath in attrfiles:
            fi2.update(attrfiles[rmtpath])
        yield fi2

def sync_link(fi):
    localpath = fi['path']
    logging.info('sync link %s', localpath)

    if path.lexists(localpath):
        logging.debug('link exists')
        if not path.islink(localpath):
            logging.error('remote link to local non-link %s', localpath)
            return
        # same check
        if os.readlink(localpath) == fi['link']:
            return True
        else: # remove if not same
            os.remove(localpath)
    # create
    os.symlink(fi['link'], localpath)
    return True

def apply_meta(filist):
    for fi in filist:
        if fi['type'] == stat.S_IFLNK:
            if not sync_link(fi):
                continue

        mode = fi['mode']
        logging.info('chmod %s %s', fi['path'], oct(mode))
        os.chmod(fi['path'], mode)
        uid = api.get_userid(fi['user'])
        gid = api.get_groupid(fi['group'])
        logging.info('chown %s %d %d', fi['path'], uid, gid)
        os.lchown(fi['path'], uid, gid)

def merge_ready2run(r2r):
    for syncinfo in r2r:
        if 'run' not in syncinfo:
            continue
        run = syncinfo['run']
        if isinstance(run, basestring):
            yield run
        if hasattr(run, '__iter__'):
            for i in run:
                yield i

def run_commands(cmds):
    for cmd in cmds:
        logging.warning('run: %s', cmd)
        os.system(cmd)

def sync_desc_back(desc):
    import yaml # import here 2 avoid import in remote
    allfilist = []
    with remote.connect(
            desc['hostname'],
            (remote.SshSudoChannel, remote.BinaryEncoding)) as rmt:
        remote.autoset_loglevel(rmt)

        for syncinfo in desc['synclist']:
            rmtpath, localpath, partten = get_syncinfo(rmt, desc, syncinfo)
            logging.warning('sync %s in %s to %s.', rmtpath, str(rmt), localpath)

            filist = rmt.apply(api.walkdir, rmtpath, None, partten)
            sync_dir(filist, rmtpath, localpath)
            f2sync = chk4files(filist, rmtpath, localpath)
            sync_files_back(rmt, f2sync, filist)
            allfilist.extend(filist)

        doc = metafile.filist_dump(allfilist, desc)
        doc = yaml.dump(doc)
        with open('%s.meta' % desc['hostname'], 'wb') as fo:
            fo.write(doc)

def sync_desc_to(desc):
    import yaml # import here 2 avoid import in remote
    allfilist, ready2run = [], []
    with open('%s.meta' % desc['hostname'], 'rb') as fi:
        doc = fi.read()
    attrs = yaml.load(doc)
    attrs = metafile.filist_load(attrs)
    cache_default_attr(attrs)

    with remote.connect(
            desc['hostname'],
            (remote.SshSudoChannel, remote.BinaryEncoding)) as rmt:
        remote.autoset_loglevel(rmt)

        for syncinfo in desc['synclist']:
            rmtpath, localpath, partten = get_syncinfo(rmt, desc, syncinfo)
            logging.warning('sync %s to %s in %s', localpath, rmtpath, str(rmt))

            filist = api.walkdir(localpath, os.getcwd(), partten)
            rmt.apply(sync_dir, filist, localpath, rmtpath)
            f2sync = rmt.apply(chk4files, filist, localpath, rmtpath)
            sync_files_to(rmt, f2sync, filist)
            if f2sync:
                ready2run.append(syncinfo)
            filist = list(merge_filist(filist, attrs, rmtpath, localpath))
            allfilist.extend(filist)

        rmt.apply(apply_meta, filist)
        cmds = list(merge_ready2run(ready2run))
        rmt.apply(run_commands, cmds)
