#!/usr/bin/env python

from distutils.core import setup

setup(name='Splonebox Python Client',
      version='0.1',
      author='bontric',
      description='client implementation to communicate with the splonebox core',
      packages=['splonecli', 'splonecli.api', 'splonecli.rpc'],
      requires=['msgpack'],
      license='GNU Lesser General Public License v3')
