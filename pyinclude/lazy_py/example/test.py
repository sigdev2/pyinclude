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

import os
import sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), r'..')))
import lazy
import pprint

if __name__ == r'__main__':
    text = r''' tes/*t t'*/e'xt /*h'g/*'jgh*/ j' kjhkj /* hlkjlkj 'hk*/jh'''

    pp = pprint.PrettyPrinter(indent=4, depth=6)

    stateParse = lazy.lazy(lazy.lazy_tokenize(text, [r'/*', r'*/', r'//', '\'\'\'', r'"""']))
    stateParse.group(lazy.lazy_stateTable(
    [
        [r'"', { r'none' : r'string', r'string' : r'none' }],
        ['\'', { r'none' : r'onestring', r'onestring' : r'none' }],
        ['\'\'\'', { r'none' : r'treeonestring', r'treeonestring' : r'none' }],
        [r'"""', { r'none' : r'treestring', r'treestring' : r'none' }],
        [r'/*', { r'none' : r'multi'}],
        [r'*/', { r'multi' : r'none'}],
        [r'//', { r'none' : r'single' }],
        [r'#', { r'none' : r'directive' }],
        ['\n', { r'single' : r'none', r'directive' : r'none' }]
    ]), lambda a, v, s : a + v, '')

    accum = []
    stateParse.value(accum.append)
    pp.pprint(accum)