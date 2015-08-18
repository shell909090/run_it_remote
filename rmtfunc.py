#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-08-14
@author: shell.xu
'''
import sys, subprocess
import local
rmt = local.RemoteFunction()

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
    import pprint
    pprint.pprint(get_dpkg())

if __name__ == '__main__': main()
