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
import getopt
import logging
from os import path
import yaml
import remote, remote.__main__
import api, sync

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

def sync_desc(desc):
    ChanCls = type('C', (remote.SshSudoChannel, remote.BinaryEncoding), {})
    with remote.Remote(ChanCls(desc['hostname'])) as rmt:
        for syncinfo in desc['synclist']:
            remote = syncinfo['remote']
            if remote.startswith('~'):
                remote = rmt.apply(path.expanduser, remote)

            partten = None
            if '*' in remote:
                partten, remote = path.basename(remote), path.dirname(remote)
                logging.info('rmt: %s, partten: %s' % (remote, partten))
                if '*' in remote:
                    raise Exception('match just allow in last level.')

            local = syncinfo.get('local') or remote
            if local.startswith(path.sep):
                local = local[1:]
            local = path.join(desc['hostname'], local)

            if '-b' in optdict:
                sync.sync_back(
                    rmt, remote, local, syncinfo.get('recurse', True), partten)
            else:
                sync.sync_to(
                    rmt, remote, local, syncinfo.get('recurse', True), partten)

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

    remote.__main__.parallel_map_t(sync_desc, desces)

if __name__ == '__main__': main()
