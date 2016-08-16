__author__ = 'katharine'

from setuptools import setup, find_packages
from pkg_resources import resource_string

requirements_str = resource_string(__name__, 'requirements.txt')
requirements = [line.strip() for line in requirements_str.splitlines()]

setup(name='pypkjs',
      version='1.0.4',
      description='A Pebble phone app simulator written in Python',
      url='https://github.com/pebble/pypkjs',
      author='Pebble Technology Corporation',
      author_email='katharine@pebble.com',
      license='MIT',
      packages=find_packages(),
      install_requires=requirements,
      package_data={
          'pypkjs.javascript.navigator': ['GeoLiteCity.dat'],
          'pypkjs.PyV8.darwin64': ['_PyV8.so'],
          'pypkjs.PyV8.linux32': ['_PyV8.so'],
          'pypkjs.PyV8.linux64': ['_PyV8.so', 'libboost_python.so.1.53.0', 'libboost_system-mt.so.1.53.0',
                           'libboost_thread-mt.so.1.53.0'],
          'pypkjs.timeline': ['layouts.json'],
      },
      entry_points={
          'console_scripts': [
            'pypkjs=pypkjs.runner.websocket:run_tool'
          ],
      },
      zip_safe=False)
