#!/usr/bin/env python
# -*- coding: utf-8 -*-

r''' Copyright 2018, SigDev

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License. '''

from setuptools import setup, find_packages
from os.path import join, dirname, realpath
import lazy

setup(name=lazy.__name__,
      version=lazy.__version__,
      packages=find_packages(exclude=[r'example']),
      description=r'Lazy calculations for Python',
      long_description=open(join(dirname(__file__), r'README.rst')).read(),
      author=lazy.__author__,
      license=lazy.__license__,
      url=r'http://github.com/sigdev2/lazy_py',
      keywords=r' '.join([
        r'python', r'lazy', r'parser', r'iterator', r'map', r'reduce', r'filter', r'parsing'
        ]
      ),
      classifiers=[
        r'Intended Audience :: Developers',
        r'Intended Audience :: System Administrators',
        r'License :: OSI Approved :: Apache Software License',
        r'Operating System :: OS Independent',
        r'Programming Language :: Python',
        r'Topic :: Software Development',
        r'Topic :: Software Development :: Libraries',
        r'Topic :: Software Development :: Libraries :: Python Modules'
        r'Topic :: Text Processing',
        r'Programming Language :: Python :: 2.6',
        r'Programming Language :: Python :: 2.7',
        r'Programming Language :: Python :: 3',
        r'Programming Language :: Python :: 3.2',
        r'Programming Language :: Python :: 3.3',
        r'Programming Language :: Python :: Implementation :: PyPy',
        ],
      install_requires=[],
      entry_points={},
      zip_safe=False
)
