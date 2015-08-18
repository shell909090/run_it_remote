#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-08-14
@author: shell.xu
'''
import sys, subprocess
import local
# import bs4
rmt = local.RemoteFunction()

def callback(hostname):
    print 'hostname: ' + hostname

@rmt.func
def get_hostname_cb():
    import remote
    with open('/etc/hostname') as fi:
        remote.channel.apply(callback, fi.read().strip())

def get_hostname():
    with open('/etc/hostname') as fi:
        return fi.read().strip()

@rmt.func
def get_dpkg():
    rslt = []
    for i, line in enumerate(subprocess.check_output(['dpkg', '-l']).splitlines()):
        if i < 6: continue
        # if line.startswith('ii'): continue
        line = line.strip()
        r = line.split()
        if r[1].startswith('python'): rslt.append(r[:3])
    return rslt

def main():
    i = local.SshInstance(sys.argv[1])
    rmt.bind(i)
    # import pprint
    # pprint.pprint(get_dpkg())
    get_hostname_cb()

if __name__ == '__main__': main()
