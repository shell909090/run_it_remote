#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-08-14
@author: shell.xu
'''
import subprocess

def get_hostname():
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
