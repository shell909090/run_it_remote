# Run Your Code Remotely

# 如何使用

试试:

    python main.py hostname rmtfunc.get_dpkg

屏幕上应当打印出hostname这台机器上所有以python开头的包。

注意：hostname这台机器应当是一台debian/ubuntu。因为get_dpkg这个函数，如同名字暗示的一样，是通过读取dpkg -l来工作的。

# 工作原理

1. 启动一个python实例，用-c执行启动代码。启动代码会读取stdin中的输入，unmarshal，编译，并执行。
2. 从stdin中，将core.py发送过去。
3. core.py会读取一个个消息，unmarshal，编译，执行，返回结果。因此就可以在远程执行任意代码了。

* sys.stdout被处理过。所有打印数据都会marshal后发给服务器端去打印。
* import也做过处理。每当你导入一个模块时，core.py会接替工作，请求main.py找到他并发过来。而后这个模块就可以像本地模块一样用了。
* C扩展是以二进制形式发送的。所以当你需要使用C扩展时，服务器和客户端必须在同一个架构上。

# 开发接口

main.py里有例子:

    h = RemoteHost(hostname)
	h.execute('xxx')
	result = h.eval('xxx')
	h.run_single('xxx; xxx')
	h.close()

## eval, execute和run_single的区别

eval只接受一个表达式，会返回表达式的值。

execute可以接受一系列语句（甚至是一个模块），但是只会返回None。

run_single可以接受一系列语句，执行每一条，得到表达式的值。并打印非None的返回值。

你可以在[python doc](https://docs.python.org/2/library/functions.html#compile)找到更多信息。
