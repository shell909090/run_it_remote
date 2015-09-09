#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-09-02
@author: Shell.Xu
@copyright: 2015, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
import os
import sys
import stat
import getopt
import logging
from os import path
import yaml
import remote, remote.__main__
import api
import metafile
import sync

optdict = {}
args = []

def limit_attr(fi, attrs):
    rslt = {}
    for k, v in fi.iteritems():
        if k in attrs:
            rslt[k] = v
    return rslt

def listdesc(dirname):
    for filename in os.listdir(dirname):
        if not filename.endswith('.yaml'):
            continue
        hostname = filename[:-5]
        with open(path.join(dirname, filename)) as fi:
            desc = yaml.load(fi.read())
        if 'hostname' not in desc:
            desc['hostname'] = hostname
        yield desc

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

def merge_filist(filist, attrs, rmtbase, local):
    attrfiles = attrs['filelist']
    for fi in filist:
        fi2 = limit_attr(fi, set(['user', 'group', 'path', 'mode', 'type']))

        if fi['type'] in (stat.S_IFREG, stat.S_IFLNK):
            fi2.update(attrs['file'])
        elif fi['type'] == stat.S_IFDIR:
            fi2.update(attrs['dir'])
        fi2.update()

        rmtpath = sync.reloca_path(fi['path'], local, rmtbase)
        fi2['path'] = rmtpath
        if rmtpath in attrfiles:
            fi2.update(attrfiles[rmtpath])
        yield fi2

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

def sync_desc_back(desc):
    ChanCls = type('C', (remote.SshSudoChannel, remote.BinaryEncoding), {})
    with remote.Remote(ChanCls(desc['hostname'])) as rmt:
        if '-l' in optdict:
            rmt.monkeypatch_logging(optdict['-l'])
        allfilist = []

        for syncinfo in desc['synclist']:
            rmtpath, local, partten = get_syncinfo(rmt, desc, syncinfo)
            logging.warning('sync %s in %s to %s.', remote, str(rmt), local)

            filist = rmt.apply(api.walkdir, rmtpath, None, partten)
            sync.sync_dir(filist, rmtpath, local)
            sync.sync_file_back(rmt, rmtpath, local, filist)
            allfilist.extend(filist)

        doc = metafile.filist_dump(
            allfilist,
            desc.get('user'), desc.get('group'),
            desc.get('filemode'), desc.get('dirmode'))
        with open('%s.meta' % desc['hostname'], 'wb') as fo:
            fo.write(doc)

def sync_desc_to(desc):
    ChanCls = type('C', (remote.SshSudoChannel, remote.BinaryEncoding), {})
    with remote.Remote(ChanCls(desc['hostname'])) as rmt:
        if '-l' in optdict:
            rmt.monkeypatch_logging(optdict['-l'])
        allfilist, ready2run = [], []

        with open('%s.meta' % desc['hostname'], 'rb') as fi:
            attrs = metafile.filist_load(fi.read())
        cache_default_attr(attrs)

        for syncinfo in desc['synclist']:
            rmtpath, local, partten = get_syncinfo(rmt, desc, syncinfo)
            logging.warning('sync %s to %s in %s', local, rmtpath, str(rmt))

            filist = api.walkdir(local, os.getcwd(), partten)
            f2sync = sync.sync_file_to(rmt, rmtpath, local, filist)
            if f2sync:
                ready2run.append(syncinfo)
            filist = list(merge_filist(filist, attrs, rmtpath, local))
            allfilist.extend(filist)

        rmt.apply(sync.apply_meta, filist)
        cmds = list(merge_ready2run(ready2run))
        rmt.apply(sync.run_commands, cmds)

def main():
    '''
    -b: sync back.
    -l: log level.
    -h: help, you just seen.
    -m: machine list.
    -t: sync to.
    '''
    global optdict
    global args
    optlist, args = getopt.getopt(sys.argv[1:], 'bl:hm:t')
    optdict = dict(optlist)
    if '-h' in optdict:
        print main.__doc__
        return

    if '-l' in optdict:
        logging.basicConfig(level=optdict['-l'].upper())

    if '-b' not in optdict and '-t' not in optdict:
        print 'you must set sync back or sync to.'
        return

    machine_allow = []
    if '-m' in optdict:
        machine_allow = optdict['-m'].split(',')

    desces = []
    for dirname in args:
        for desc in listdesc(dirname):
            if not desc['synclist']: continue
            if machine_allow and desc['hostname'] not in machine_allow:
                continue
            desces.append(desc)

    if '-b' in optdict:
        sync_desc = sync_desc_back
    else:
        sync_desc = sync_desc_to
    remote.__main__.parallel_map_t(sync_desc, desces)

if __name__ == '__main__': main()
