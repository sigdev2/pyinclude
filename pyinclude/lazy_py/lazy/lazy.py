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

import re
import copy

class Command:
    def __init__(self, f):
        self.op = f

class Sublist(list):
    pass

class IteratorsTree:
    def __init__(self, it):
        self.it = it
        self.parent = None
        self.i = None
    def __next__(self):
        return self.next()
    def next(self):
        return next(self.it)

class IteratorEx:
    def __init__(self, obj):
        self.__obj = obj
        self.__commands = []
        self.__it = IteratorsTree(iter(self.__obj))
        self.__current = None
        self.__idx = -1

    def __iter__(self):
        return self
    
    def __next__(self):
        return self.next()
    
    def __xrange(self, num):
        if not hasattr(__builtins__, r'xrange'):
            return range(num)
        return xrange(num)

    def next(self):
        item = None
        done = True
        buffer = []
        while(True):
            try:
                item = next(self.__it)
                done = False
            except StopIteration:
                done = True
                while self.__it.parent != None:
                    self.__it = self.__it.parent
                    try:
                        item = next(self.__it)
                        done = False
                        break
                    except StopIteration:
                        continue

            if done == False:
                buffer.append(item)
            start = self.__it.i
            for i in self.__xrange(len(self.__commands)):
                is_skip = False
                while True:
                    if start != None:
                        i = start
                        start = None

                    if i >= len(self.__commands):
                        break
                    ret = self.__commands[i].op(item, done, buffer, self)

                    if ret == False: # skip
                        is_skip = True
                    else:
                        if ret == True: # don't change
                            pass
                        elif ret == r'repeat': # repeat
                            continue
                        elif ret == r'done':
                            raise StopIteration
                        elif isinstance(ret, Sublist): # buffer, hasattr(ret, r'__iter__')
                            if len(buffer) > 0:
                                buffer.pop()
                            it = IteratorsTree(iter(ret))
                            it.i = i + 1
                            it.parent = self.__it
                            self.__it = it
                            # note: clear buffer is operation duty
                            is_skip = True
                        else: # value
                            item = ret
                            if len(buffer) <= 0:
                                buffer.append(item)
                            else:
                                buffer[-1] = item
                    break
                if is_skip:
                    break
            if is_skip:
                continue
            break

        self.__current = item
        self.__idx += 1
        return item

    def clean(self):
        self.__it = IteratorsTree(iter(self.__obj))
        self.__current = None
        self.__idx = -1

    def map(self, f):
        def mapLambda(val, done, buffer, it):
            if done:
                return r'done'
            val = f(val)
            return val

        self.__commands.append(Command(mapLambda))
        return self

    def filter(self, f):
        def filterLambda(val, done, buffer, it):
            if done:
                return r'done'
            return f(val)
        self.__commands.append(Command(filterLambda))
        return self

    def remove(self, value):
        def removeLambda(val, done, buffer, it):
            if done:
                return r'done'
            if isinstance(value, list):
                return not val in value
            return val != value
        self.__commands.append(Command(removeLambda))
        return self

    def group(self, f, g):
        def groupLambda(val, done, buffer, it):
            if done:
                if len(buffer) > 0:
                    out = []
                    for i in self.__xrange(len(buffer)):
                        out.append(buffer.pop(0))
                    return g(out, done)
                return r'done'
            if f(val, buffer):
                return False # skip
            # buffer is full
            out = []
            for i in self.__xrange(len(buffer)):
                out.append(buffer.pop(0))
            return g(out, done)

        self.__commands.append(Command(groupLambda))
        return self

    def scan(self, f):
        def scanLambda(val, done, buffer, it):
            if done:
                return r'done'
            ret = f(val)
            if not isinstance(ret, list):
                return val
            return Sublist(ret)

        self.__commands.append(Command(scanLambda))
        return self

class Token:
    def __init__(self, token, types = [], state = None):
        try:
            rx_obj = re._pattern_type
        except:
            rx_obj = re.Pattern
        
        if callable(token):
            self.check = token
            self.part = token
            self.type = r'func'
        elif isinstance(token, rx_obj):
            self.type = r'rx'
            self.check = lambda v: token.match(r''.join(v) if isinstance(v, list) else v)
            self.part = lambda v: token.match(r''.join(v) if isinstance(v, list) else v)
        elif isinstance(token, list) and len(token) == 2 and isinstance(token[0], rx_obj) and isinstance(token[1], rx_obj):
            self.check = lambda v: token[0].match(r''.join(v) if isinstance(v, list) else v)
            self.part = lambda v: token[1].match(r''.join(v) if isinstance(v, list) else v)
            self.type = r'rx'
        elif isinstance(token, list) and len(token) == 2 and callable(token[0]) and callable(token[1]):
            self.type = r'func'
            self.check = token[0]
            self.part = token[1]
        elif len(token) > 2 and token[0] == r'/' and token[-1] == r'/':
            self.type = r'rx'
            rx = re.compile(token)
            self.check = lambda v: rx.match(r''.join(v) if isinstance(v, list) else v)
            self.part = lambda v: rx.match(r''.join(v) if isinstance(v, list) else v)
        elif isinstance(token, list) and len(token) == 2 and len(token[0]) > 2 and token[0][0] == r'/' and token[0][-1] == r'/' and len(token[1]) > 2 and token[1][0] == r'/' and token[1][-1] == r'/':
            self.type = r'rx'
            rx1 = re.compile(token[0])
            rx2 = re.compile(token[1])
            self.check = lambda v: rx1.match(r''.join(v) if isinstance(v, list) else v)
            self.part = lambda v: rx2.match(r''.join(v) if isinstance(v, list) else v)
        elif isinstance(token, list):
            self.type = r'list'
            self.check = lambda v: r''.join(token) == r''.join(v)
            self.part = lambda v: r''.join(token[:len(v)] if isinstance(v, list) else token[:1]) == r''.join(v)
        else:
            self.type = r'str'
            self.check = lambda v: token == (r''.join(v) if isinstance(v, list) else v)
            self.part = lambda v: token.startswith(r''.join(v) if isinstance(v, list) else v)

        self.types = set(types)
        self.state = token if state == None else state
        self.token = token

    def token_type(self):
        return self.type
    def has(self, typeName):
        return typeName in self.types
    def add(self, typeName):
        return self.types.add(typeName)
    def __len__(self):
        return len(self.token)

class Grouper(object):
    def __init__(self, s):
        self.source = s
    def bufferize(self, buff, done):
        if len(buff) == 0:
            return False
        if len(buff) == 1:
            return buff[0]
        if done:
            return r''.join(buff)
        last = buff.pop(-1)
        return Sublist([r''.join(buff), last])
    def filter(self, value, buffer):
        return True
    def __iter__(self):
        return IteratorEx(self.source).group(
            lambda v, b: self.filter(v, b),
            lambda x, d: self.bufferize(x, d))  

class Wordizer(Grouper):
    def filter(self, value, buffer):
        return '\'";:.,></?|\\=-+)({}[]*&^%$#@!`~\t\n\r '.find(value) <= -1

# LL(1)
class LL1StateTokenizer(Grouper):
    def __init__(self, s, l):
        super(LL1StateTokenizer, self).__init__(s)
        self.__list = l
    
    def bufferize(self, buff, done):
        if len(buff) == 0:
            return False
        if len(buff) == 1:
            return buff[0]
        return r''.join(buff)

    def  __iter__(self):
        local = { r'state' : r'none' }
        def stateFilter(v, buff):
            for val in self.__list:
                if val.check(v):
                    if local[r'state'] == r'none':
                        if r'start' in val.types:
                            local[r'state'] = val.state
                            break
                    else:
                        if r'end' in val.types and len(set(local[r'state']) & set(val.state)) > 0:
                            local[r'state'] = r'none'
                            break
            return local[r'state'] != r'none'

        return IteratorEx(self.source).group(stateFilter, lambda x, d: self.bufferize(x, d))

# LL(1)
class LL1TableTokenizer(Grouper):
    def __init__(self, s, table, recursive = False):
        super(LL1TableTokenizer, self).__init__(s)
        self.__table = table
        self.__recursive = recursive

    def __compileStackedBuffer(self, buff, allstak=False):
        if len(buff) <= 2:
            return buff
        if self.__recursive:
            buff[-2].append(buff.pop())
        else:
            buff[-2] += buff.pop()
        if allstak:
            return self.__compileStackedBuffer(buff, allstak)
        return buff
    
    def __lastDownFloor(self, stack, n = 0):
        if n == 0:
            return stack
        return self.__lastDownFloor(stack[-1], n - 1)

    def  __iter__(self):
        local = { r'stack' : [r'none'], r'stack_buffer' : [[]], r'up': True }
        def stateFilter(v, buff):
            for val in self.__table:
                token = val[0]
                if (hasattr(token, r'check') and token.check(v)) or token == v:
                    stateTable = val[1]
                    if callable(stateTable):
                        newstate = stateTable(v, local[r'stack'][-1])
                    else:
                        newstate = stateTable[local[r'stack'][-1]]
                    if local[r'stack'][-1] != newstate:
                        if local[r'stack'][-1] == r'none':
                            local[r'stack'].append(newstate)
                            local[r'stack_buffer'].append([])
                            local[r'up'] = True
                        else:
                            if newstate == r'none':
                                local[r'stack'] = [r'none']
                                local[r'stack_buffer'] = self.__compileStackedBuffer(local[r'stack_buffer'], True)
                                local[r'up'] = False
                            elif len(local[r'stack']) > 1 and local[r'stack'][-2] == newstate:
                                local[r'stack'] = local[r'stack'][:-1]
                                local[r'stack_buffer'] = self.__compileStackedBuffer(local[r'stack_buffer'])
                                local[r'up'] = False
                            else:
                                local[r'stack'].append(newstate)
                                local[r'stack_buffer'].append([])
                                local[r'up'] = True
                        return False
                    break
            return local[r'stack'][-1] != r'none'
    
        def bufferFunc(buff, done):
            if len(buff) == 0:
                return False

            if local[r'stack'][-1] == r'none':
                if len(local[r'stack_buffer']) > 0 and len(local[r'stack_buffer'][-1]) > 0:
                    local[r'stack_buffer'][-1] += buff
                    if self.__recursive:
                        out = copy.deepcopy(local[r'stack_buffer'][-1])
                    else:
                        out = r''.join(local[r'stack_buffer'][-1])
                    local[r'stack_buffer'].pop()
                    return out
                else:
                    return r''.join(buff)
            else:
                if self.__recursive:
                    if len(buff) == 1:
                        local[r'stack_buffer'][-1].append(buff[0])
                    elif local[r'up']:
                        local[r'stack_buffer'][-2] += buff[:-1]
                        local[r'stack_buffer'][-1].append(buff[-1])
                    else:
                        floor = self.__lastDownFloor(local[r'stack_buffer'], len(local[r'stack_buffer']))
                        floor += buff
                else:
                    local[r'stack_buffer'][-1] += buff

                
            return False

        return IteratorEx(self.source).group(stateFilter, bufferFunc)

class SubToken:
    def __init__(self, token, pos):
        self.pos = pos
        self.token = token

# LL(k)
class LLKTokenizer(Grouper):
    def __init__(self, s, l):
        super(LLKTokenizer, self).__init__(s)
        self.__list = l

    def  __iter__(self):
        local = { r'variants': [] }
        def filterGroup(v, buff):
            # add new buffers
            for val in self.__list:
                if val.part(v):
                    local[r'variants'].append(SubToken(val, len(buff) - 1))

            # choose actuals buffers
            new_variants = []
            for val in local[r'variants']:
                token = val.token
                buffer = buff[val.pos:]

                if token.part(buffer):
                    if token.check(buffer):
                        local[r'variants'] = [val]
                        return False # send buffer

                    new_variants.append(val)

            local[r'variants'] = new_variants
            return True # skip
        
        def groupBuffer(buff, done):
            if len(local[r'variants']) <= 0:
                return Sublist(buff)

            subtoken = local[r'variants'][0]
            buffer = buff[subtoken.pos:]
            data = buff[0:subtoken.pos]
            data.append(r''.join(buffer))
            local[r'variants'] = []
            return Sublist(data)
        
        return IteratorEx(self.source).group(filterGroup, groupBuffer)

# LL(k) greedy, but regular grammar is leazy
class LLKGreedyTokenizer(Grouper):
    def __init__(self, s, l):
        super(LLKGreedyTokenizer, self).__init__(s)
        self.__list = l
        
        sort_map = dict()
        func_and_rx = []
        for val in self.__list:
            if hasattr(val, r'__len__'):
                vallen = len(val)
                if not vallen in sort_map:
                    sort_map[vallen] = []
                sort_map[vallen].append(val)
            else:
                func_and_rx.append(val)

        keys = sorted(list(sort_map.keys()), reverse=True)
        self.multi = self.source
        for val in keys:
            self.multi = LLKTokenizer(self.multi, sort_map[val])
        self.multi = LLKTokenizer(self.multi, func_and_rx)

    def __iter__(self):
        return iter(self.multi)


def stateTable(table):
    def calc(key, state):
        for val in table:
            if (hasattr(val[0], r'check') and val[0].check(key)) or key == val[0]:
                if state in val[1]:
                    return val[1][state]
        return state
    return calc

def stringStates(tokens):
    d = {}
    for token in tokens:
        sub_state = r''
        old_state = r'none'
        for ch in token:
            sub_state += ch
            if ch == token[-1]:
                sub_state = r'none'
            if ch in d:
                d[ch][old_state] = sub_state
            else:
                d[ch] = {old_state : sub_state}
            old_state = sub_state

    for ss in tokens:
        if r'/.*/' in d:
            d[r'/.*/'][ss] = r'none'
        else:
            d[r'/.*/'] = {ss : r'none'}

    ret = []
    for k in d.keys():
        ret.append([k, d[k]])
    return stateTable(ret)

def tokenizer(text, tokens):
    return LLKGreedyTokenizer(Wordizer(text), tokens)

def state_tokenizer(text, tokens):
    return LL1StateTokenizer(LLKGreedyTokenizer(Wordizer(text), tokens), tokens)

def table_tokenizer(text, tokens, table):
    return LL1TableTokenizer(LL1StateTokenizer(LLKGreedyTokenizer(Wordizer(text), tokens), tokens), table)

if __name__ == r'__main__':
    pass