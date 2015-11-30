__author__ = 'katharine'

import os
import sys
from setuptools import setup, find_packages

requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')

with open(requirements_path) as requirements_file:
  requirements = [line.strip() for line in requirements_file.readlines()]

setup(name='pypkjs',
      version='3.6',
      description='PebbleKit JS in Python!',
      url='https://github.com/pebble/pypkjs',
      author='Pebble Technology Corporation',
      author_email='katharine@pebble.com',
      license='MIT',
      packages=find_packages(),
      install_requires=requirements,
      package_data={
          'javascript.navigator': 'GeoLiteCity.dat'
      },
      entry_points={
          'console_scripts': [
            'pypkjs=runner.websocket:run_tool'
          ],
      },
      zip_safe=False)
