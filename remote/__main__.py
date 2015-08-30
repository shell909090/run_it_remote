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
import local

def parallel_map_t(func, it, concurrent=20):
    from multiprocessing.pool import ThreadPool
    pool = ThreadPool(concurrent)
    for i in it:
        pool.apply_async(func, (i,))
    pool.close()
    pool.join()

def get_source(infile):
    for line in infile:
        yield line.strip()

def prepare_instance():
    global inscls
    inscls = local.SshInstance
    if '-i' not in optdict:
        return
    if optdict['-i'] == 'sudo':
        inscls = local.SudoSshInstance
        return
    if optdict['-i'] == 'network':
        inscls = local.NetInstance
        return
    module_name, funcname = optdict['-i'].rsplit('.', 1)
    module = __import__(module_name)
    inscls = getattr(module, funcname)

def prepare_hostlist():
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
    with inscls(host) as ins:
        for command in args:
            prepare_modules(ins, command)
            result = ins.eval(command)
            result = json.dumps(result)
            if '-M' in optdict:
                print '%s: %s' % (host, result)
            else:
                print result

def run_single_host(host):
    with inscls(host) as ins:
        for command in args:
            print '-----%s output: %s-----' % (host, command)
            ins.single(command)

def main():
    '''
    -c: input hostlist from stdin.
    -e: eval mode. normally run in single mode.
    -f: input hostlist from file.
    -i: instance mode. can be network and sudo. class name also acceptable.
    -j: dump result as json mode.
    -l: log level.
    -h: help, you just seen.
    -M: print with hostname.
    -m: host list as parameter.
    -p: run in parallel.
    '''
    global optdict
    global args
    optlist, args = getopt.getopt(sys.argv[1:], 'cef:i:jl:hMm:p')
    optdict = dict(optlist)
    if '-h' in optdict:
        print main.__doc__
        return

    if '-l' in optdict:
        logging.basicConfig(level=optdict['-l'])
        
    prepare_instance()
    hostlist = prepare_hostlist()
    if hostlist is None:
        return

    run_host = run_single_host
    if '-e' in optdict:
        run_host = run_eval_host

    if '-p' in optdict:
        return parallel_map_t(run_host, hostlist)
    map(run_host, hostlist)

if __name__ == '__main__': main()
