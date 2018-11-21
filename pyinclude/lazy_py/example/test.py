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
import six
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), r'..')))
import lazy

def wordizerTest(text):
    print(r' - '.join(lazy.Wordizer(text)))

def tokenizerParser(text, tokens):
    print(r' - '.join(lazy.tokenizer(text, tokens)))

def stateParserTest(text, tokens):
    print(r' - '.join(lazy.state_tokenizer(text, tokens)))

def fucArgsParserTest(text, tokens, table):
    print(r' - '.join(lazy.table_tokenizer(text, tokens, table)))

def recJoin(out, sep = r' - '):
    if isinstance(out, six.string_types):
        return out
    s = r''
    for it in out:
        if len(s) > 0:
            s += sep
        if isinstance(it, six.string_types):
            s += it
        else:
            s += str(it)
    return s

def recursiveParserTest(text, tokens, table):
    print(recJoin(lazy.LL1TableTokenizer(lazy.LL1StateTokenizer(lazy.LLKGreedyTokenizer(lazy.Wordizer(text), tokens), tokens), table, True)))

if __name__ == r'__main__':
    text = r'''_tes/*t t'*/ext /*h'g/*'jgh*//*sdfsf*/ /*spec sdfss*/gdfgdfg spec*/ { sdfsdf {sdfsd} jhghg }{ sdfsdf {sdfsd} jhghg }somefunc(sdfs(dfsd(f))'sdfsdf)') j' kjhkj /* hlkjlkj 'hk*/jh'''
    tokens = [lazy.Token(r'/*', [r'start'], [r'mult']),
              lazy.Token(r'*/', [r'end'], [r'mult']),
              lazy.Token('\'', [r'end', r'start'], [r'onestring']),
              lazy.Token([r'/', r'*', r'spec'], [r'start'], [r'spec']),
              lazy.Token([r'spec', r'*', r'/'], [r'end'], [r'spec'])]
    
    tokensArgs = [
              lazy.Token([r'somefunc', r'(']),
              lazy.Token('\'', [r'end', r'start'], [r'onestring']),
              lazy.Token(r'/*', [r'start'], [r'mult']),
              lazy.Token(r'*/', [r'end'], [r'mult']),
              lazy.Token([r'/', r'*', r'spec'], [r'start'], [r'spec']),
              lazy.Token([r'spec', r'*', r'/'], [r'end'], [r'spec'])]
    
    local = { r'count': 0, r'count_rec': 0 }
    
    def args(val, state):
        if state == r'none':
            if False:
                if val == r'(':
                    local[r'count'] += 1
                    return r'in_args'
        elif state == r'in_args':
            if val == r'(':
                local[r'count'] += 1
            elif val == r')':
                local[r'count'] -= 1
            if local[r'count'] <= 0:
                return r'none'
        return state
    
    def recursiveArgs(val, state):
        if val == r'{':
            local[r'count_rec'] += 1
            return r'in_args' + str(local[r'count_rec'])
        elif val == r'}':
            local[r'count_rec'] -= 1
            if local[r'count_rec'] <= 0:
                return r'none'
            return r'in_args' + str(local[r'count_rec'])
        return state
    
    def function(val, state):
        if state == r'none':
            local[r'count'] += 1
            return r'in_args'
        return state
    table = [
        [r'somefunc(', function],
        [r'(', args],
        [r')', args],
    ]

    recTable=[
        [r'{', recursiveArgs],
        [r'}', recursiveArgs]
    ]

    wordizerTest(text)
    print(r'')
    tokenizerParser(text, tokens)
    print(r'')
    stateParserTest(text, tokens)
    print(r'')
    fucArgsParserTest(text, tokensArgs, table)
    print(r'')
    recursiveParserTest(text, tokensArgs, recTable)
    print(r'')