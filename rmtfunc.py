#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-08-14
@author: shell.xu
@copyright: 2015, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
import sys, logging, subprocess
# import bs4

def callback(hostname):
    print 'hostname: ' + hostname

def get_hostname_cb():
    from remote import remote
    with open('/etc/hostname') as fi:
        remote.channel.apply(callback, fi.read().strip())

def get_hostname():
    logging.info('get hostname')
    with open('/etc/hostname') as fi:
        return fi.read().strip()

def get_dpkg():
    rslt = []
    for i, line in enumerate(subprocess.check_output(['dpkg', '-l']).splitlines()):
        if i < 6: continue
        # if line.startswith('ii'): continue
        line = line.strip()
        r = line.split()
        if r[1].startswith('python'): rslt.append(r[:3])
    return rslt
