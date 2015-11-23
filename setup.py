__author__ = 'katharine'

import sys
from setuptools import setup, find_packages

requires = [
  'backports.ssl-match-hostname==3.4.0.2',
  'gevent>=1.1b5',
  'gevent-websocket==0.9.3',
  'greenlet==0.4.9',
  'peewee==2.4.7',
  'pygeoip==0.3.2',
  'pypng==0.0.17',
  'python-dateutil==2.4.1',
  'requests==2.5.0',
  'sh==1.09',
  'six==1.9.0',
  'websocket-client==0.31.0',
  'wsgiref==0.1.2',
  'libpebble2==0.0.12',
  'netaddr==0.7.18'
]

packages = find_packages()
print packages

setup(name='pypkjs',
      version='3.6',
      description='PebbleKit JS in Python!',
      url='https://github.com/pebble/pypkjs',
      author='Pebble Technology Corporation',
      author_email='katharine@pebble.com',
      license='MIT',
      packages=packages,
      install_requires=requires,
      entry_points={
          'console_scripts': [
            'pypkjs=runner.websocket:run_tool'
          ],
      },
      zip_safe=True)