#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-03-11
@author: shell.xu
'''
import re
import sys
import json
import base64
import getopt
import subprocess

def check_output(x):
    p = subprocess.Popen(x, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    r = p.stdout.read()
    p.wait()
    return r.splitlines()

def split_reader(src, sep, keys, stopblank=False):
    for line in src:
        if stopblank and not line:
            return
        r = line.split(sep, 1)
        if len(r) == 1:
            continue
        k, v = r[0].strip(), r[1].strip()
        if k.lower() in keys:
            yield k, v

DMI_INFO = {
    'system': set(['serial number', 'uuid']),
    'base': set(['product name', 'version', 'serial number']),
    'processor': set(['id', 'version']),
    'memory': set([
        'size', 'locator', 'speed', 'manufacturer', 'serial number',
        'asset tag', 'part number', 'configured'])}
def dmidecode():
    try: src = iter(check_output(['dmidecode',]))
    except:
        exc_info = sys.exc_info()
        yield 'Base', 'error'
        raise exc_info[0], exc_info[1], exc_info[2]
    for line in src:
        if not line or line.startswith('Handle'):
            continue
        # FIXME: Error here
        name = line.split()[0]
        info = DMI_INFO.get(name.lower())
        if not info:
            continue
        r = dict(split_reader(src, ':', info, True))
        if not r:
            continue
        if name == 'Memory' and not r.get('Serial Number'):
            continue
        yield name, r

SMART_INFO = ['vendor', 'model family', 'product', 'device model', 
              'user capacity', 'logical block size', 'serial number']
re_disk = re.compile(r'(sd[a-z]+)\d*')
def diskinfo():
    disks = set()
    with open('/proc/diskstats', 'r') as fdisk:
        for line in fdisk:
            m = re_disk.match(line.split()[2])
            if m: disks.add(m.group(1))
    for disk in disks:
        try:
            output = check_output(['smartctl', '-i', '/dev/%s' % disk])
            info = dict(split_reader(output, ':', SMART_INFO))
            info['disk'] = disk
            yield 'Disk', info
        except:
            exc_info = sys.exc_info()
            yield 'Disk', {'disk': disk, 'state': 'error'}
            raise exc_info[0], exc_info[1], exc_info[2]

def diskusage():
    df = check_output(['df', '-k', '-P'])
    for line in df[1:]:
        d = line.strip().split()
        yield 'DiskUsage', {'dev': d[0], 'total': d[1], 'used': d[2], 'mountpoint': d[5]}

re_iface = re.compile(r'^(\d+): (.+): <(.*)> (.*)')
def ipaddr():
    iface, ips, macs, rslt = '', [], [], {}
    for line in check_output(['ip', 'addr']):
        if line.startswith(' '):
            r = line.strip().split()
            if r[0] == 'inet':
                ips.append(r[1])
            elif r[0] == 'link/ether':
                macs.append(r[1])
            continue
        if iface:
            try: unicode(iface)
            except UnicodeDecodeError:
                iface = 'Base64ed:' + base64.b64encode(iface)
            rslt.update({'iface': iface, 'ipaddr': ips, 'ether': macs})
            yield rslt
            ips, macs = [], []
        m = re_iface.match(line)
        i = iter(m.group(4).split())
        iface, rslt = m.group(2), dict(zip(i, i))
    try: unicode(iface)
    except UnicodeDecodeError:
        iface = 'Base64ed:' + base64.b64encode(iface)
    rslt.update({'iface': iface, 'ipaddr': ips, 'ether': macs})
    yield rslt

ETH_INFO = ['speed', 'duplex', 'auto-negotiation']
def ethtool(iface):
    src = iter(check_output(['ethtool', iface]))
    return dict(split_reader(src, ':', ETH_INFO))

def ethinfo():
    for info in ipaddr():
        d = ethtool(info['iface'])
        if d:
            info.update(d)
        yield 'Network', info

def memusage():
    free = check_output(['free', '-m'])
    total = int(free[1].split()[1])
    used = int(free[2].split()[2])
    yield 'MemoryUsage', {'total': total, 'used': used}

def hostname():
    with open('/etc/hostname') as fi:
        return [('Hostname', fi.read().strip())]

def run_info(funcs):
    rslt = {}
    for f in funcs:
        try:
            for k, v in f():
                rslt.setdefault(k, []).append(v)
        except:
            import traceback
            rslt.setdefault('Error', []).append(traceback.format_exc())
    return rslt

def all_info():
    return run_info([dmidecode, diskinfo, diskusage,
                     ethinfo, memusage, hostname])

def main():
    '''
    -h: help
    -i: indent
    '''
    optlist, _ = getopt.getopt(sys.argv[1:], 'hi')
    optdict = dict(optlist)
    if '-h' in optdict:
        print main.__doc__
        return

    info = all_info()
    try: s = json.dumps(info, indent=4 if '-i' in optdict else None)
    except: s = json.dumps({'Hostname': hostname()[0][1], 'Error': 'json error'})
    sys.stdout.write(s + '\n')
    sys.stdout.flush()

if __name__ == '__main__': main()
