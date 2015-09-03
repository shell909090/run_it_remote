#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-08-30
@author: Shell.Xu
@copyright: 2015, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
import os, sys
import json
import getopt
import logging
import traceback
import local

def parallel_map_t(func, it, concurrent=20):
    from multiprocessing.pool import ThreadPool
    pool = ThreadPool(concurrent)
    def wrapper(i):
        try:
            return func(i)
        except Exception as err:
            print traceback.format_exc()
    for i in it:
        pool.apply_async(wrapper, (i,))
    pool.close()
    pool.join()

def get_source(infile):
    for line in infile:
        yield line.strip()

def name2obj(name):
    module_name, funcname = name.rsplit('.', 1)
    module = __import__(module_name)
    return getattr(module, funcname)

def parse_channel():
    if '-n' not in optdict or optdict['-n'] == 'ssh':
        return local.SshChannel
    if optdict['-n'] == 'sudo':
        return local.SshSudoChannel
    return name2obj(optdict['-n'])

def parse_protocol():
    if '-p' not in optdict or optdict['-p'] == 'binary':
        return local.BinaryEncoding
    if optdict['-p'] == 'base64':
        return local.Base64Encoding
    return name2obj(optdict['-p'])

def parse_hostlist():
    if '-c' in optdict:
        return get_source(sys.stdin)
    elif '-f' in optdict:
        fi = open(optdict['-f'])
        return get_source(fi)
    elif '-m' in optdict:
        return optdict['-m'].split(',')
    else:
        print 'can\'t find host list.'
        print 'you may define by stdin(-c), file(-f) or machine(-m).'
        return None

def prepare_modules(ins, command):
    if '(' not in command:
        return
    funcname = command.split('(', 1)[0]
    if '.' not in funcname:
        return
    module_name = funcname.rsplit('.', 1)[0]
    ins.execute('import ' + module_name)

def run_eval_host(host):
    with local.Remote(ChannelClass(host)) as rmt:
        for command in args:
            prepare_modules(rmt, command)
            result = rmt.eval(command)
            result = json.dumps(result)
            if '-M' in optdict:
                print '%s: %s' % (host, result)
            else:
                print result

def run_single_host(host):
    with local.Remote(ChannelClass(host)) as rmt:
        for command in args:
            print '-----%s output: %s-----' % (host, command)
            rmt.single(command)

def main():
    '''
    -c: input hostlist from stdin.
    -f: input hostlist from file.
    -j: dump result as json mode.
    -l: log level.
    -h: help, you just seen.
    -M: print with hostname.
    -m: host list as parameter.
    -n: channel mode, local, ssh or sudo.
    -p: protocol mode, binary or base64, or other class.
    -s: run in serial mode.
    -x: eval mode. normally run in single mode.
    '''
    global optdict
    global args
    optlist, args = getopt.getopt(sys.argv[1:], 'cf:jl:hMm:n:p:sx')
    optdict = dict(optlist)
    if '-h' in optdict:
        print main.__doc__
        return

    if '-l' in optdict:
        logging.basicConfig(level=optdict['-l'].upper())

    chancls = parse_channel()
    protcls = parse_protocol()
    global ChannelClass
    class ChannelClass(chancls, protcls):
        pass

    hostlist = parse_hostlist()
    if hostlist is None:
        return

    run_host = run_single_host
    if '-x' in optdict:
        run_host = run_eval_host

    if '-s' in optdict:
        return map(run_host, hostlist)
    return parallel_map_t(run_host, hostlist)

if __name__ == '__main__': main()