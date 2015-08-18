# Run Your Code Remotely

[Chinese README](README.zh.md)

# How to use

try this:

    python local.py -m host1,host2 'import pprint,rmtfunc; pprint.pprint(rmtfunc.get_dpkg())'

it will return all your packages start with 'python' in machine 'hostname'.

Attention: hostname should be a debian/ubuntu. cause get_dpkg, as it named, are gather information from dpkg -l.

# How it works

1. Run bootstrap code in a python instance. The bootstrap code will read stdin, unmarshal it, compile, and run.
2. Sent core.py from stdin.
3. core.py will read a new message, unmarshal it, run, and return result. So you can run anything remotely.

* sys.stdout is hooked, so print data will send back by marshal to a message.
* import is hooked. every time you try to import some module. main.py will find it, and send it to core.py. And it will be loaded as native module.
* C extension are send as binary file. When you wanna use C extension, server and client must in same arch.

# How developer use it

As main.py:

    h = SshInstance(hostname)
	h.execute('xxx')
	result = h.eval('xxx')
	h.run_single('xxx; xxx')
	h.close()

## difference between execute and eval

eval just accept a sigle expression, and will evaluate it as the return value.

execute accept a sequence of statements, but just return None.

single accept a single interactive statement. print every thing other than None.

You can get more information from [python doc](https://docs.python.org/2/library/functions.html#compile).
