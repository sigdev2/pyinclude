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

import glob
import os
import re
import codecs
import six
import copy
try:
    # Python 2.6-2.7 
    from HTMLParser import HTMLParser
except ImportError:
    # Python 3
    from html.parser import HTMLParser
import sys
from .lazy_py import lazy

class SafeExecuteRecurseLocals:
    def __init__(self, **entries):
        self.__dict__.update(entries)
    def __getitem__(self, key):
        value = None
        if key in self.__dict__:
            value = copy.copy(self.__dict__[key])
            loc = SafeExecuteRecurseLocals(**self.__dict__)
            del loc.__dict__[key]
            try:
                value = IncludeParser.safe_eval(value, loc)
            except:
                if isinstance(value, str) or isinstance(value, six.string_types):
                    value = IncludeParser.html_parser.unescape(value)
                value = IncludeParser.replaceMaros(value, loc)
        return value

class IncludeParser:
    included = []
    macros = {}
    declaraions = {}
    start_ends = set()
    excludes = set()
    tokens = set()
    state_table = []
    strings_state = [
                    [r'"', { r'none' : r'string', r'string' : r'none' }],
                    ['\'', { r'none' : r'onestring', r'onestring' : r'none' }]
                ]
    commands = {
        r'include': re.compile(r'^\s*(import|import_once|inc|include|require|include_once|require_once)?\s+(\'[^\']+?\'|"[^"]+?")(?:\s+(once|\d+))?\s*$', re.M or re.S),
        r'if': re.compile(r'^\s*if\s+([^$]*)\s*$', re.M or re.S),
        r'elif': re.compile(r'^\s*(?:elif|else\s*if)\s+([^$]*)\s*$', re.M or re.S),
        r'else': re.compile(r'^\s*else\s*$', re.M or re.S),
        r'endif': re.compile(r'^\s*endif|fi\s*$', re.M or re.S),
        r'undef': re.compile(r'^\s*(?:del|delete|undef|remove)\s+([A-z][A-z_0-9]*)\s*$', re.M or re.S),
        r'define': re.compile(r'^\s*(?:def|define|macro|macros)\s+([A-z][A-z_0-9]*)(?:(?:(\([^\)]+\))?\s*[\=\:]?\s*|\s*[\=\:]\s*|\s+)([^$]+))?\s*$', re.M or re.S),

        r'directive':  re.compile(r'^\s*(?:directive|direct|declare|declaration|decl)\s+([A-z][A-z_0-9]*)\s+([^$]*)\s*$', re.M or re.S)
    }
    reserved = [r'import', r'import_once', r'inc', r'include', r'require', r'include_once', r'require_once',
                r'if', r'elif', r'else', r'endif', r'fi',
                r'del', r'delete', r'undef', r'remove',
                r'def', r'define', r'macro', r'macros',
                r'directive', r'direct', r'declare', r'declaration', r'decl']
    safe_rx = re.compile(r'eval|__[A-z]+__', re.M or re.S)
    html_parser = HTMLParser()

    def clear():
        IncludeParser.included = []
        IncludeParser.macros = {}
        IncludeParser.declaraions = {}
        IncludeParser.start_ends = set()
        IncludeParser.excludes = set()
        IncludeParser.tokens = set()
        IncludeParser.state_table = []
    clear = staticmethod(clear)

    def argsParse(s):
        local = { r'count' : 0, '\'' : False, r'"' : False, '\'\'\'' : False, r'"""' : False}
        def st(val, state):
            if val == '\'' and not (local[r'"'] or local['\'\'\''] or local[r'"""']):
                local[val] = not local[val]
            if val == r'"' and not (local['\''] or local['\'\'\''] or local[r'"""']):
                local[val] = not local[val]
            if val == '\'\'\'' and not (local[r'"'] or local['\''] or local[r'"""']):
                local[val] = not local[val]
            if val == r'"""' and not (local[r'"'] or local['\''] or local['\'\'\'']):
                local[val] = not local[val]

            if val == r'(':
                local[r'count'] += 1
                if state == r'none':
                    return r'in_args'
            elif val == r')':
                local[r'count'] -= 1
                if state == r'in_args' and local[r'count'] == 0:
                    return r'none'
            return state
        return lazy.lazy(s).group(st, lambda a, v, s: a + v, r'').reduce(lambda x, y : x + [y], [])
    argsParse = staticmethod(argsParse)

    def toString(obj):
        if isinstance(obj, str) or isinstance(obj, six.string_types):
            return obj
        return str(obj)
    toString = staticmethod(toString)

    def safe_eval(cmd, loc = None):
        if loc == None:
            loc = SafeExecuteRecurseLocals(**IncludeParser.macros)
        env = {}
        env[r'locals']   = None
        env[r'globals']  = None
        env[r'__name__'] = None
        env[r'__file__'] = None
        env[r'__builtins__'] = None

        cmd = re.sub(IncludeParser.safe_rx, r'', cmd)
        return eval(cmd, env, loc)
    safe_eval = staticmethod(safe_eval)

    def safe_bool_eval(cmd, loc = None):
        if loc == None:
            loc = SafeExecuteRecurseLocals(**IncludeParser.macros)
        try:
            return bool(IncludeParser.safe_eval(cmd, loc))
        except:
            print(r'Wrong if expressin')
        return False
    safe_bool_eval = staticmethod(safe_bool_eval)

    def replaceMaros(data, loc=None):
        data = IncludeParser.toString(data)
        if len(data) > 0:
            if loc == None:
                loc = SafeExecuteRecurseLocals(**IncludeParser.macros)
            rx = re.compile(r'(?:^|(?<=\W))(' + r'|'.join(loc.__dict__.keys()) + r')(?=\W|$)(\([^\)]+\))?', flags=re.M or re.S)
            start = 0
            end = 0
            out = r''
            for m in re.finditer(rx, data):
                end = m.start()
                if start < end:
                    out += m.string[start:end]
                macros_name, args = m.groups()
                if macros_name != None: 
                    value = loc[macros_name]
                    if value == None:
                        out += m.string[m.start():m.end()]
                    else:
                        if not isinstance(value, str) and not isinstance(value, six.string_types):
                            if callable(value):
                                if args == None:
                                    value = IncludeParser.macros[macros_name]
                                else:
                                    part = m.string[m.start():]
                                    parsed = IncludeParser.argsParse(part)
                                    try:
                                        value = IncludeParser.toString(IncludeParser.safe_eval(macros_name + parsed[1], loc))
                                        out += value
                                        start = m.start() + len(parsed[0]) + len(parsed[1])
                                        continue
                                    except:
                                        value = m.string[m.start():m.end()]
                            else:
                                value = str(value)
                        out += value

                start = m.end()
            if end != 0:
                if len(data) - start > 0:
                    out += data[start:-1]
                data = out
        return data
    replaceMaros = staticmethod(replaceMaros)

    def concat_strings(accum, v):
        if (v.startswith('\'') and v.endswith('\'')) or (v.startswith(r'"') and v.endswith(r'"')):
            return accum + v[1:-1]
        else:
            return accum + v
        v = v.split(r'.')
        for part in v:
            if part in IncludeParser.macros:
                val = IncludeParser.macros[part]
                if (val.startswith('\'') and val.endswith('\'')) or (val.startswith(r'"') and val.endswith(r'"')):
                    accum += val[1:-1]
                else:
                    accum += val
            else:
                accum += part
        return accum
    concat_strings = staticmethod(concat_strings)

    def convertPath(self, path):
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        sep = os.path.sep
        if sep != r'/':
            path = path.replace(sep, r'/')
        return path

    def __init__(self, root = os.getcwd(), start_ends = [], excludes = [], macro_vars = [], encoding=r'utf-8', recurse=[]):
        self.root = self.convertPath(root)
        self.if_stack = []
        self.recurse = recurse
        self.encoding = encoding

        if len(macro_vars) > 0:
            IncludeParser.macros.update(macro_vars)
        if len(IncludeParser.start_ends) <= 0 and len(start_ends) > 0:
            IncludeParser.start_ends = start_ends
            for s, e in IncludeParser.start_ends:
                IncludeParser.tokens.add(s)
                IncludeParser.tokens.add(e)
                IncludeParser.tokens.add('\\' + e)
                if s == e:
                    IncludeParser.state_table.append([s, { r'none' : s + s, s + s : r'none' }])
                else:
                    IncludeParser.state_table.append([s, { r'none' : s + e }])
                    IncludeParser.state_table.append([e, { s + e : r'none' }])
            if len(excludes) > 0:
                IncludeParser.excludes = excludes
                for s, e in excludes:
                    IncludeParser.tokens.add(s)
                    IncludeParser.tokens.add(e)
                    if len(e) == 1:
                        IncludeParser.tokens.add('\\' + e)
                    if s == e:
                        IncludeParser.state_table.append([s, { r'none' : s + s, s + s : r'none' }])
                    else:
                        IncludeParser.state_table.append([s, { r'none' : s + e }])
                        IncludeParser.state_table.append([e, { s + e : r'none' }])
    
    def parse(self, data):
        stateParse = lazy.lazy(lazy.lazy_tokenize(data, IncludeParser.tokens))
        stateParse.group(lazy.lazy_stateTable(IncludeParser.state_table), lambda a, v, s : a + v, '')

        local = { r'out' : r'', r'skip' : False }
        parent = self
        def calculate(token):
            command = False
            for s, e in IncludeParser.start_ends:
                if token.startswith(s) and token.endswith(e):
                    command = token[len(s):-len(e)]
                    break
            
            if command == False or len(command) <= 0:
                if not local[r'skip']:
                    if isinstance(command, bool):
                        finded = False
                        for s, e in IncludeParser.excludes:
                            if token.startswith(s) and token.endswith(e):
                                local[r'out'] += token
                                finded = True
                                break
                        if not finded:
                            local[r'out'] += IncludeParser.replaceMaros(token)
                    elif len(command) <= 0:
                        local[r'out'] += token
                return

            ret = parent.command(local[r'skip'], command)

            if local[r'skip']:
                if ret == r'unskip':
                    local[r'skip'] = False
            else:
                if ret == r'skip':
                    local[r'skip'] = True
                elif isinstance(ret, str) or isinstance(ret, six.string_types):
                    local[r'out'] += ret
                elif ret == False:
                    local[r'out'] += token
        
        stateParse.value(calculate)
        return local[r'out']
    
    def command(self, skip, code):
        code = code.strip()
        for short in IncludeParser.declaraions.keys():
            if code.startswith(short):
                code = code.replace(short, IncludeParser.declaraions[short], 1)
                break

        for cmd in IncludeParser.commands.keys():
            if skip:
                if cmd != r'elif' and cmd != r'else' and cmd != r'endif':
                    continue
            
            ret = IncludeParser.commands[cmd].search(code)
            if ret == None:
                continue
            
            if cmd == r'include':
                keyword, full_path, count = ret.groups()
                if keyword != None and keyword.endswith(r'_once'):
                    count = r'once'
                if count == None:
                    count = 1
                if full_path == None:
                    return False
                path = lazy.lazy(full_path).group(lazy.lazy_stateTable(IncludeParser.strings_state), lambda a, v, s : a + v, r'').reduce(lambda x, y : IncludeParser.concat_strings(x, y), r'')
                
                if not os.path.isabs(path):
                    path = os.path.join(self.root, path)

                out = r''
                names = glob.glob(path)
                for name in names:
                    out += self.includeFile(name, count)
                return out
            elif cmd == r'define':
                macros, args, value = ret.groups()
                if macros == None:
                    return False
                if value == None:
                    value = 1
                if args != None:
                    groups = IncludeParser.argsParse(code)
                    value = r'(lambda ' + groups[1][1:-1] + r' : ' + r''.join(groups[2:]) + r')'
                IncludeParser.macros[macros] = value
                return True
            elif cmd == r'undef':
                macro = ret.groups()
                if macro == None:
                    return False
                else:
                    macro = macro[0].strip()
                if macro in IncludeParser.macros:
                    del IncludeParser.macros[macro]
                return True
            elif cmd == r'if':
                value = False
                if not value in self.if_stack: 
                    expression = ret.groups()
                    if expression != None:
                        expression = expression[0].strip()
                        value = IncludeParser.safe_bool_eval(expression)
                self.if_stack.append(value)
                if  value == False:
                    return r'skip'
                return True
            elif cmd == r'elif' and len(self.if_stack) > 0:
                value = False
                if not value in self.if_stack[:-1]: 
                    if self.if_stack[-1] == True:
                        self.if_stack[-1] = False
                        return r'skip'
                    expression = ret.groups()
                    if expression != None:
                        expression = expression[0].strip()
                        value = IncludeParser.safe_bool_eval(expression)
                self.if_stack[-1] = value
                if  value == False:
                    return r'skip'
                return r'unskip'
            elif cmd == r'else' and len(self.if_stack) > 0:
                if False in self.if_stack[:-1]:
                    return r'skip'
                if self.if_stack[-1] == True:
                    self.if_stack[-1] = False
                    return r'skip'
                self.if_stack[-1] = True
                return r'unskip'
            elif cmd == r'endif' and len(self.if_stack) > 0:
                old = self.if_stack[-1]
                self.if_stack = self.if_stack[:-1]
                parent = len(self.if_stack) <= 0 or self.if_stack[-1] == True
                if parent != old:
                    if False in self.if_stack:
                        return r'skip'
                    return r'unskip' if parent else r'skip'
                return True
            elif cmd == r'directive':
                name, direct = ret.groups()
                if name == None:
                    return False
                if name in IncludeParser.reserved:
                    return False
                if name in IncludeParser.declaraions and direct == None:
                    del IncludeParser.declaraions[name]
                    return True
                if direct == None:
                    return False

                IncludeParser.declaraions[name] = direct
                return True

            break
        return False

    def includeFile(self, path, count):
        path = self.convertPath(path)

        if path in self.recurse:
            return r''

        if path in IncludeParser.included:
            return r''
        if count == r'once':
            count = 1
        else:
            if not isinstance(count, int):
                count = int(count)
        
        if not os.path.exists(path):
            return r''
        
        self.recurse.append(path)
        
        out = r''
        for _ in range(count):
            data = r''
            with codecs.open(path, r'r', self.encoding) as f:
                data = f.read()
            parser = IncludeParser(os.path.dirname(path), encoding=self.encoding, recurse=self.recurse)
            data = parser.parse(data)
            out += data
        self.recurse = self.recurse[:-1]
        
        if count == r'once':
            IncludeParser.included.append(path)
        return out

def parse(text, start_ends = [], excludes = [], macro_vars = [], encoding=r'utf-8', root = os.getcwd()):
    parser = IncludeParser(root, start_ends, excludes, macro_vars, encoding)
    return parser.parse(text)

def include(path, start_ends = [], excludes = [], macro_vars = [], encoding=r'utf-8', count=1):
    parser = IncludeParser(os.path.dirname(path), start_ends, excludes, macro_vars, encoding)
    return parser.includeFile(path, count)

if __name__ == r'__main__':
    pass