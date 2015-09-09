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
import remote
import sync

optdict = {}

def get_desces():
    dirname = '.'
    machine_allow = []
    if '-m' in optdict:
        machine_allow = optdict['-m'].split(',')

    for filename in os.listdir(dirname):
        if not filename.endswith('.yaml'):
            continue
        hostname = filename[:-5]

        with open(path.join(dirname, filename)) as fi:
            desc = yaml.load(fi.read())
        if 'hostname' not in desc:
            desc['hostname'] = hostname

        if not desc['synclist']: continue
        if machine_allow and desc['hostname'] not in machine_allow:
            continue
        yield desc

def main():
    '''
    -b: sync back.
    -l: log level.
    -h: help, you just seen.
    -m: machine list.
    -t: sync to.
    '''
    global optdict
    optlist, _ = getopt.getopt(sys.argv[1:], 'bl:hm:t')
    optdict = dict(optlist)
    if '-h' in optdict:
        print main.__doc__
        return

    if '-l' in optdict:
        logging.basicConfig(level=optdict['-l'].upper())

    if '-b' not in optdict and '-t' not in optdict:
        print 'you must set sync back or sync to.'
        return

    desces = get_desces()

    if '-b' in optdict:
        sync_desc = sync.sync_desc_back
    else:
        sync_desc = sync.sync_desc_to
    remote.parallel_map_t(sync_desc, desces)

if __name__ == '__main__': main()
