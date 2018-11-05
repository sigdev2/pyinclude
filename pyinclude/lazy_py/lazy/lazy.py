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

from copy import copy, deepcopy
import re

class Command:
    t = 0
    f = None

    r'''note:
    enum  t = 0 - Map, t = 1 - Filter  '''
    def __init__(self, f, t = 0):
        self.t = t
        self.f = f

class IteratorEx:
    obj = []
    commands = []
    c = True
    it = None

    def __init__(self, obj, commands = [], chain = True):
        self.obj = obj
        self.commands = commands
        self.c = chain

    def lazy_exec(self, v):
        if isinstance(self.commands, list):
            exit = True
            for cmd in self.commands:
                if cmd.t == 0:
                    v = cmd.f(v)
                elif not cmd.f(v):
                    exit = False
                    break
            if exit:
                return True, v
        else:
            if self.commands.t == 0:
                v = self.commands.f(v)
                return True, v
            elif self.commands.f(v):
                return True, v
        return False, v
    
    def next(self):
        v = None
        try:
            v = next(self.it, None)
            while v != None:
                has, v = self.lazy_exec(v)
                if has:
                    break
                v = next(self.it, None)
        except StopIteration:
            pass
        return v
    
    def filter(self, f):
        cmd = Command(f, 1)
        if self.c:
            self.commands.append(cmd)
            return self
        new_commands = copy(self.commands)
        new_commands.append(cmd)
        return IteratorEx(self.obj, new_commands, self.c)
    
    def remove(self, val):
        f = None
        if isinstance(val, list):
            f = lambda v : val != v
        else:
            f = lambda v : not v in val
        cmd = Command(f, 1)
        if self.c:
            self.commands.append(cmd)
            return self
        new_commands = copy(self.commands)
        new_commands.append(cmd)
        return IteratorEx(self.obj, new_commands, self.c)

    def map(self, f):
        cmd = Command(f, 0)
        if self.c:
            self.commands.append(cmd)
            return self
        new_commands = copy(self.commands)
        new_commands.append(cmd)
        return IteratorEx(self.obj, new_commands, self.c)

    def groupLiner(self, f, r, init = None):
        local = { r'state' : r'none', r'accum' : deepcopy(init), r'hasVal' : False }
        def state_filter(v):
            if v == r'__EOF':
                if local[r'state'] != r'none':
                    local[r'state'] = r'none'
                    local[r'hasVal'] = True
                ret = local[r'accum']
                local[r'accum'] = deepcopy(init)
                if not local[r'hasVal']:
                    return r'__EOF'
                local[r'hasVal'] = False
                return ret
            newstate = f(v, local[r'state'])
            if newstate != r'none':
                local[r'accum'] = r(local[r'accum'], v, local[r'state'])
                local[r'state'] = newstate
                local[r'hasVal'] = True
                return None
            local[r'state'] = newstate
            ret = v
            if local[r'hasVal']:
                ret = r(local[r'accum'], v, local[r'state'])
                local[r'accum'] = deepcopy(init)
                return ret
            return ret

        cmd1 = Command(state_filter, 0)
        cmd2 = Command(lambda v : v != None, 1)
        
        if self.c:
            self.commands.append(cmd1)
            self.commands.append(cmd2)
            return self        
        
        new_commands = copy(self.commands)
        new_commands.append(cmd1)
        new_commands.append(cmd2)
        return IteratorEx(self.obj, new_commands, self.c)

    def group(self, f, r, init = None):
        local = { r'stack' : [r'none'], r'accum' : deepcopy(init), r'hasVal' : False }
        def state_filter(v):
            state = local[r'stack'][-1]
            if v == r'__EOF':
                if state != r'none':
                    local[r'stack'] = [r'none']
                    local[r'hasVal'] = True
                ret = local[r'accum']
                local[r'accum'] = deepcopy(init)
                if not local[r'hasVal']:
                    return r'__EOF'
                local[r'hasVal'] = False
                return ret

            newstate = f(v, state)
            if newstate == state:
                local[r'accum'] = r(local[r'accum'], v, local[r'stack'])
                local[r'hasVal'] = True
                return None        
            ret = local[r'accum']
            local[r'accum'] = deepcopy(init)
            local[r'hasVal'] = False

            if len(local[r'stack']) > 1 and local[r'stack'][-2] == newstate:
                ret = r(ret, v, local[r'stack'])
                local[r'stack'] = local[r'stack'][:-1]
            else:
                local[r'stack'].append(newstate)
                local[r'accum'] = r(local[r'accum'], v, local[r'stack'])
            return ret

        cmd1 = Command(state_filter , 0)
        cmd2 = Command(lambda v : v != None, 1)
        
        if self.c:
            self.commands.append(cmd1)
            self.commands.append(cmd2)
            return self

        new_commands = copy(self.commands)
        new_commands.append(cmd1)
        new_commands.append(cmd2)
        return IteratorEx(self.obj, new_commands, self.c)

    def reduce(self, f, init = None):
        self.it = iter(self.obj)
        ret = deepcopy(init)
        val = self.next()
        while val != None:
            ret = f(ret, val)
            val = self.next()
        v = r'__EOF'
        _, v = self.lazy_exec(v)
        if v != r'__EOF':
            ret = f(ret, v)
        return ret

    def value(self, f):
        self.it = iter(self.obj)
        val = self.next()
        while val != None:
            f(val)
            val = self.next()
        v = r'__EOF'
        _, v = self.lazy_exec(v)
        if v != r'__EOF':
            f(v)
    
    def join(self, sep = r''):
        return self.reduce(lambda p, n : p + n if p == r'' else p + sep + n, r'')

def multiCheck(checker, val):
    if checker == None:
        return False
    if callable(checker):
        return checker(val)
    elif isinstance(checker, str):
        l = len(checker)
        if l > 2 and checker[0] == r'/' and checker[-1] == r'/':
            if val == None:
                return False
            return re.match(checker[1:-1], val, re.S or re.M) != None
    return checker == val

def lazy_stateTable(table):
    def calc(key, state):
        for val in table:
            if multiCheck(val[0], key):
                if state in val[1]:
                    return val[1][state]
        return state
    return calc

def lazy_stringStates(tokens):
    d = {}
    states = set()
    substates = set()
    for s in tokens:
        if s in states:
            continue
        states.add(s)
        
        sub_state = r''
        old_state = r'none'
        for ch in s:
            sub_state += ch
            if ch in d:
                d[ch][old_state] = sub_state
            else:
                d[ch] = {old_state : sub_state}
            substates.add(sub_state)

        for ss in substates:
            if r'/.*/' in d:
                d[r'/.*/'][ss] = r'none'
            else:
                d[r'/.*/'] = {ss : r'none'}
    
    keys = list(d.keys())
    keys.remove(r'/.*/')
    keys.append(r'/.*/')
    ret = []
    for k in keys:
        ret.append([k, d[k]])
    return lazy_stateTable(ret)

def lazy(obj, chain = True):
    return IteratorEx(obj, [], chain)

def lazy_tokenize(text, tokens):
    def reduceComments(a, v):
        if v in tokens:
            a.append(v)
        else:
            for ch in v:
                a.append(ch)
        return a
    return lazy(text).groupLiner(lazy_stringStates(tokens),
    lambda a, v, s : a + v, r'').reduce(reduceComments, [])

if __name__ == r'__main__':
    pass