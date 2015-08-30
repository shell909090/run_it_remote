# Run Your Code Remotely

# 如何使用

试试:

    python -m remote -m host1,host2 'import pprint,rmtfunc; pprint.pprint(rmtfunc.get_dpkg())'

屏幕上应当打印出hostname这台机器上所有以python开头的包。

注意：hostname这台机器应当是一台debian/ubuntu。因为get_dpkg这个函数，如同名字暗示的一样，是通过读取dpkg -l来工作的。

# 更多例子

试试:

    python -m remote -e -i sudo -p -m host1,host2 'hwinfo.all_info()'

这应当会打出远程机器的配置。

* -e是使用eval模式工作的意思，结果会被收集回来，使用json格式打印出来。
* -i是instance模式选择，这里使用sudo在远程执行。
* -p是并行工作。
* -m是机器列表，也可以用-f或-c指定。
* hwinfo.all_info是附带的收集机器信息的程序。

# 工作原理

1. 启动一个python实例，用-c执行启动代码。启动代码会读取stdin中的输入，unmarshal，编译，并执行。
2. 从stdin中，将core.py发送过去。
3. core.py会读取一个个消息，unmarshal，编译，执行，返回结果。因此就可以在远程执行任意代码了。

* sys.stdout被处理过。所有打印数据都会marshal后发给服务器端去打印。
* import也做过处理。每当你导入一个模块时，core.py会接替工作，请求main.py找到他并发过来。而后这个模块就可以像本地模块一样用了。
* C扩展是以二进制形式发送的。所以当你需要使用C扩展时，服务器和客户端必须在同一个架构上。

# 开发接口

main.py里有例子:

    h = SshInstance(hostname)
	h.execute('xxx')
	result = h.eval('xxx')
	h.run_single('xxx; xxx')
	h.close()

## eval, execute和run_single的区别

eval只接受一个表达式，会返回表达式的值。

execute可以接受一系列语句（甚至是一个模块），但是只会返回None。

single可以接受一系列语句，执行每一条，得到表达式的值。并打印非None的返回值。

你可以在[python doc](https://docs.python.org/2/library/functions.html#compile)找到更多信息。

# License

Copyright (c) 2015, Shell.Xu <shell909090@gmail.com>
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
