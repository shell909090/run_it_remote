# Run Your Code Remotely

[Chinese README](README.zh.md)

# How to use

try this:

    python main.py hostname rmtfunc.get_dpkg

it will return all your packages in machine 'hostname'.

# How it works

1. Run bootstrap code in a python instance, get stdin and stdout. The bootstrap code will read stdin, unmarshal it, compile, and run.
2. Sent core.py from stdin.
3. core.py will read a new message, unmarshal it, run, and return result. So you can run anything remotely.

* sys.stdout is hooked, so print data will send back by marshal to a message.
* import is hooked. every time you try to import some module. main.py will find it, and send it to core.py. core.py will load it as native module.

# How developer use it

As main.py:

    h = RemoteHost(hostname)
	h.execute('xxx')
	result = h.eval('xxx')
	h.close()

## difference between execute and eval

Eval just accept a sigle expression, and will evaluate it as the return value.

Execute accept a sequence of statements, but just return None.

You can get more information from [python doc](https://docs.python.org/2/library/functions.html#compile).
