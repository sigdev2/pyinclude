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
import pyinclude

setup(name=pyinclude.__name__,
      version=pyinclude.__version__,
      packages=find_packages(exclude=[r'example']),
      description=pyinclude.__desc__,
      long_description=open(join(dirname(__file__), r'README.rst')).read(),
      author=pyinclude.__author__,
      license=pyinclude.__license__,
      url=r'http://github.com/sigdev2/pyinclude',
      keywords=' '.join([
        r'preprocessor', r'python', r'templates', r'compile', 
        ]
      ),
      classifiers=[
        r'Environment :: Console',
        r'Intended Audience :: Developers',
        r'Intended Audience :: System Administrators',
        r'License :: OSI Approved :: Apache Software License',
        r'Operating System :: OS Independent',
        r'Programming Language :: Python',
        r'Topic :: Software Development',
        r'Topic :: Software Development :: Libraries :: Python Modules',
        r'Topic :: Text Processing :: General',
        r'Topic :: Utilities',
        r'Programming Language :: Python :: 2.6',
        r'Programming Language :: Python :: 2.7',
        r'Programming Language :: Python :: 3',
        r'Programming Language :: Python :: 3.2',
        r'Programming Language :: Python :: 3.3',
        r'Programming Language :: Python :: Implementation :: PyPy',
        ],
      install_requires=[],
      entry_points={
        r'console_scripts': [
          r'pyinclude = pyinclude.__main__:main',
          ]
      },
      zip_safe=False
)
