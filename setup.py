#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2015-09-07
@author: Shell.Xu
@copyright: 2015, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
from distutils.core import setup

version = '1.0'
description = 'run it remote'
long_description = ' run you python code in remote computer.
  * import module and package in server. include py/pyc, dynamic library(if can).
  * stdout print to server, so is logging.
  * push any function to remote, run and return.
  * call back.'

setup(
    name='run_it_remote', version=version,
    description=description, long_description=long_description,
    author='Shell.E.Xu', author_email='shell909090@gmail.com',
    scripts=[,], packages=['remote', 'sync'])
