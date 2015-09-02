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
    with remote.SudoSshInstance(desc['hostname']) as ins:
        for syncinfo in desc['synclist']:
            rmt = syncinfo['remote']
            if rmt.startswith('~'):
                rmt = ins.apply(path.expanduser, rmt)
            local = syncinfo.get('local') or rmt
            if local.startswith(path.sep):
                local = local[1:]
            local = path.join(desc['hostname'], local)
            if '-b' in optdict:
                sync.sync_back(
                    ins, rmt, local, syncinfo.get('recurse', True))

def main():
    '''
    -b: sync back.
    -l: log level.
    -h: help, you just seen.
    -t: sync to.
    '''
    global optdict
    global args
    optlist, args = getopt.getopt(sys.argv[1:], 'bl:ht')
    optdict = dict(optlist)
    if '-h' in optdict:
        print main.__doc__
        return

    if '-l' in optdict:
        logging.basicConfig(level=optdict['-l'].upper())

    if '-b' not in optdict and '-t' not in optdict:
        print 'you must set sync back or sync to.'
        return

    desces = []
    for dirname in args:
        for desc in listdesc(dirname):
            if not desc['synclist']: continue
            desces.append(desc)

    remote.__main__.parallel_map_t(sync_desc, desces)
    # for desc in desces:
    #     sync_desc(desc)

if __name__ == '__main__': main()
