#!/usr/bin/env python

from distutils.core import setup

setup(name='Splonebox Python Client',
      version='0.1',
      description='A client implementation to communicate with the splonebox core',
      install_requires=['pycrypto>=2.6.1', 'msgpack-python>=0.4.6'],
      packages=['splonecli', 'splonecli.api', 'splonecli.rpc', 'splonecli.os'])
