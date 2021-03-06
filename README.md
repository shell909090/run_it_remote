# Run Your Code Remotely

[Chinese README](README.zh.md)

## How to use

try this:

    python -m remote -m host1,host2 'import pprint,rmtfunc; pprint.pprint(rmtfunc.get_dpkg())'

it will return all your packages start with 'python' in machine 'hostname'.

Attention: hostname should be a debian/ubuntu. cause get_dpkg, as it named, are gather information from dpkg -l.

## more example

try this:

    python -m remote -x -n sudo -m host1,host2 'hwinfo.all_info()'

it will print all infomation about remote machine.

* -x for eval mode. result will get back and dump out as json.
* -n for channel select. we run remote by sudo.
* -m for machine list, -f(file) or -c(stdin) also can be use.
* hwinfo.all_info is a program in hwinfo.py. it will collect all infomation about remote machine.

## How it works

1. Run bootstrap code in a python instance. The bootstrap code will read stdin, unmarshal it, compile, and run.
2. Sent core.py from stdin.
3. core.py will read a new message, unmarshal it, run, and return result. So you can run anything remotely.

* sys.stdout is hooked, so print data will send back by marshal to a message.
* import is hooked. every time you try to import some module. main.py will find it, and send it to core.py. And it will be loaded as native module.
* C extension are send as binary file. When you wanna use C extension, server and client must in same arch.

## How developer use it

    chancls = type('C', (local.SshChannel, local.BinaryEncoding), {})
    with chancls(hostname) as h:
	    h.execute('xxx')
		result = h.eval('xxx')
		h.run_single('xxx; xxx')

More example, see remote/__main__.py.

## difference between execute and eval

eval just accept a sigle expression, and will evaluate it as the return value.

execute accept a sequence of statements, but just return None.

single accept a single interactive statement. print every thing other than None.

You can get more information from [python doc](https://docs.python.org/2/library/functions.html#compile).

# sync

A sync system based on project 'run it remote'. It can sync file, read/write privilege and owner. Mostly used in config files.

# License

Copyright (c) 2015, Shell.Xu <shell909090@gmail.com>
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
