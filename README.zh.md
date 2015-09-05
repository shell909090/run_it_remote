# Run Your Code Remotely

## 如何使用

试试:

    python -m remote -m host1,host2 'import pprint,rmtfunc; pprint.pprint(rmtfunc.get_dpkg())'

屏幕上应当打印出hostname这台机器上所有以python开头的包。

注意：hostname这台机器应当是一台debian/ubuntu。因为get_dpkg这个函数，如同名字暗示的一样，是通过读取dpkg -l来工作的。

## 更多例子

试试:

    python -m remote -x -n sudo -m host1,host2 'hwinfo.all_info()'

这应当会打出远程机器的配置。

* -x是使用eval模式工作的意思，结果会被收集回来，使用json格式打印出来。
* -n是channel模式选择，这里使用sudo在远程执行。
* -m是机器列表，也可以用-f或-c指定。
* hwinfo.all_info是附带的收集机器信息的程序。

## 工作原理

1. 启动一个python实例，用-c执行启动代码。启动代码会读取stdin中的输入，unmarshal，编译，并执行。
2. 从stdin中，将core.py发送过去。
3. core.py会读取一个个消息，unmarshal，编译，执行，返回结果。因此就可以在远程执行任意代码了。

* sys.stdout被处理过。所有打印数据都会marshal后发给服务器端去打印。
* import也做过处理。每当你导入一个模块时，core.py会接替工作，请求main.py找到他并发过来。而后这个模块就可以像本地模块一样用了。
* C扩展是以二进制形式发送的。所以当你需要使用C扩展时，服务器和客户端必须在同一个架构上。

## 开发接口

    chancls = type('C', (local.SshChannel, local.BinaryEncoding), {})
    with chancls(hostname) as h:
	    h.execute('xxx')
		result = h.eval('xxx')
		h.run_single('xxx; xxx')

remote/__main__.py里有进一步例子。

## eval, execute和run_single的区别

eval只接受一个表达式，会返回表达式的值。

execute可以接受一系列语句（甚至是一个模块），但是只会返回None。

single可以接受一系列语句，执行每一条，得到表达式的值。并打印非None的返回值。

你可以在[python doc](https://docs.python.org/2/library/functions.html#compile)找到更多信息。

# sync

基于run it remote的，同步远程文件和权限/属主的程序。主要用于同步配置文件。

## 工作原理

在工作目录下，包含有多个yaml文件。每个文件描述一台服务器的同步信息。

sync back模式下。从根据配置，从机器上找到合适的文件，检查其在本地是否已经存在一样的内容。如果不存在，则同步回来。最后将所有文件（无论是执行了复制还是本地已存在）的属主/权限写入描述文件。

sync to模式下。根据配置，从本地寻找合适的文件，检查是否在远程存在一样的内容。如不存在，则同步过去。最后根据描述文件内的记录，将同步过去的文件的权限和属主修改到位。

如果要同步系统文件（配置），需要root权限。因此默认以SshSudo模式运行。

注意：所有10M以上的文件会跳过不处理。

## 文件属性

* path: 文件路径。其中包含的路径可以是绝对路径也可以是相对路径。一般远程路径保存时都以绝对路径保存。
* type: 类型。在内存中是数字类型，定义参见import stat中的S_IFMT。写入文件时变换为字符串。可以取'dir', 'file', 'link'。
* mode: 权限。定义同import stat中的S_IMODE。实际上就是unix中的UGO权限。
* user: 用户名。注意是用户名字符串。
* group: 组名。也是字符串。
* md5: 文件的md5值。仅文件存在此项。
* size: 文件大小。仅文件存在此项。
* link: 链接目标。仅软链接存在此项。

## 描述文件

yaml格式，里面包含每个文件的必要属性。属性以dict方式存储。

保存时，会根据内容计算出最多的属主/属组和文件权限/目录权限，并且在最开始的common中保存。如果和common中一致，即可省略去文件项记录。

* common: dict，所有文件的默认属性。
  * username: 默认属主。
  * groupname: 默认属组。
  * filemode: 默认文件权限。
  * dirmode: 默认目录权限。
* filelist: dict。key为文件路径，value为文件属性。由于路径保存于key中，因此属性中会去掉path。其中只描述user, group, mode, type。如果其余三项和默认值一致，仅剩type一项时，该文件项即被忽略。

## 同步配置结构

* hostname: 可以服务器的hostname。如果没有指定，则按照hostname.yaml的规则，从文件名中解析。
* user: 用户名，控制权限描述文件的默认用户名。
* group: 组名，控制权限描述文件的默认组名。
* filemode: 文件权限。
* dirmode: 目录权限。
* synclist:
  * remote: 远程路径，注意需要是绝对路径，否则需要从python执行的起始路径开始计算。支持~来表示用户根目录。如果里面包含通配符，则会分为两个部分。基础路径和通配规则。
  * local: 本地路径。无论是否是绝对路径，都会被转换为相对路径，在前面加上hostname来存放。

# License

Copyright (c) 2015, Shell.Xu <shell909090@gmail.com>
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
