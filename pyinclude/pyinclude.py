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
import keyword
import collections
try:
    # Python 2.6-2.7 
    from HTMLParser import HTMLParser
except ImportError:
    # Python 3
    from html.parser import HTMLParser
import sys
from .lazy_py import lazy
try:
    # Python 2.6-2.7
    from StringIO import StringIO
except ImportError:
    # Python 3
    from io import StringIO
import contextlib

@contextlib.contextmanager
def stdoutIO(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = StringIO()
    sys.stdout = stdout
    try: 
        yield stdout
    finally:
        sys.stdout = old

class ReadOnlyDict(collections.Mapping):
    def __init__(self, data):
        self._data = data
    def __getitem__(self, key): 
        return self._data[key]
    def __len__(self):
        return len(self._data)
    def __iter__(self):
        return iter(self._data)

class ExecEnv(dict):
    def __init__(self, var, access = {}):
        self.env_locals = {}
        self.var = var
        self.consts = {
            r'locals' : lambda: ReadOnlyDict(self.env_locals),
            r'globals' :  lambda: ReadOnlyDict(self),
            r'__name__' : r'<script>',
            r'__file__' : r'<script>',
            r'__builtins__' : access
        }
        super(ExecEnv, self).__init__(self.consts)

    def chack_var_name(self, name):
        if name == None:
            return False
        if name.startswith(r'__'):
            return False
        return not (name in self.consts or name in self.consts[r'__builtins__'] or name in keyword.kwlist or name in __builtins__)
    def get_locals(self):
        return self
    def get_globals(self):
        return self
    def write_locals(self):
        for l in self.env_locals.keys():
            if self.chack_var_name(l) and not super(ExecEnv, self).__contains__(l):
                value = self.env_locals[l]
                if value != None:
                    self.var[l] = value
    def write_globals(self):
        for g in super(ExecEnv, self).keys():
            if self.chack_var_name(g):
                value = super(ExecEnv, self).__getitem__(g)
                if value != None:
                    self.var[g] = value

    # get locals
    def __getitem__(self, key):
        if super(ExecEnv, self).__contains__(key):
            return super(ExecEnv, self).__getitem__(key)
        bi = self.consts[r'__builtins__']
        if key in bi:
            return copy.deepcopy(bi[key])
        if key in self.env_locals:
            return self.env_locals[key]
        if key in self.var:
            return copy.deepcopy(self.var[key])
        return None

    # set locals
    def __setitem__(self, key, value):
        self.env_locals[key] = value

    # del locals
    def __delitem__(self, key):
        if key in self.env_locals:
            del self.env_locals[key]

    # other locals
    def __len__(self):
        return len(self.keys())
    def __iter__(self):
        return iter(self.keys())
    def __contains__(self, key):
        return super(ExecEnv, self).__contains__(key) or key in self.consts[r'__builtins__'] or key in self.env_locals or key in self.var
    def keys(self):
        return set(list(self.env_locals.keys()) + list(self.var.keys()) + list(self.consts[r'__builtins__'].keys()) + list(super(ExecEnv, self).keys()))

class SafeExecuteRecurseLocals(ExecEnv):
    def __init__(self, d, access = {}):
        super(SafeExecuteRecurseLocals, self).__init__(d, access)
    def __getitem__(self, key):
        value = copy.deepcopy(super(SafeExecuteRecurseLocals, self).__getitem__(key))
        if isinstance(value, str) or isinstance(value, six.string_types):
            loc = SafeExecuteRecurseLocals(self.var, self.consts[r'__builtins__'])
            loc.env_locals = copy.deepcopy(self.env_locals)
            loc.env_locals[key] = None
            try:
                value = IncludeParser.safe_eval(value, loc)
            except:
                value = IncludeParser.html_parser.unescape(value)
                value = IncludeParser.replaceMaros(value, loc)
        return value
    def keys(self):
        return self.var.keys()

class IncludeParser:
    included = []
    access_eval = {}
    try:
        # Python 3
        access_exec = {
            r'print' : print
        }
    except:
        # Python 2.6-2.7
        access_exec = {}

    standartd_macros = {}
    macros = copy.deepcopy(standartd_macros)
    declaraions = {}
    start_ends = set()
    excludes = set()
    excludes_tokens = set()
    excludes_states = []
    tokens = set()
    state_table = []
    string_tokens = set(['\\\'', '\\\'\'\'', '\\"', '\\"""'])
    string_states = [
                    [r'"', { r'none' : r'string', r'string' : r'none' }],
                    ['\'', { r'none' : r'onestring', r'onestring' : r'none' }],
                    ['\'\'\'', { r'none' : r'onemultistring', r'onemultistring' : r'none' }],
                    ['"""', { r'none' : r'multistring', r'multistring' : r'none' }]
                ]
    commands = {
        r'include': re.compile(r'^\s*(import|import_once|inc|include|require|include_once|require_once)?\s+(\'[^\']+?\'|"[^"]+?")(?:\s+(once|\d+))?\s*', re.DOTALL|re.MULTILINE),
        r'if': re.compile(r'^\s*if\s+(.+)\s*', re.DOTALL|re.MULTILINE),
        r'elif': re.compile(r'^\s*(?:elif|else\s*if)\s+(.+)\s*', re.DOTALL|re.MULTILINE),
        r'else': re.compile(r'^\s*else\s*', re.DOTALL|re.MULTILINE),
        r'endif': re.compile(r'^\s*(?:endif|fi)\s*', re.DOTALL|re.MULTILINE),
        r'undef': re.compile(r'^\s*(?:del|delete|undef|remove)\s+([A-z][A-z_0-9]*)\s*', re.DOTALL|re.MULTILINE),
        r'define': re.compile(r'^\s*(?:def|define|macro|macros)\s+([A-z][A-z_0-9]*)(?:(?:(\([^\)]+\))?\s*[\=\:\s]?\s*|\s*[\=\:\s]\s*)(.+))?\s*', re.DOTALL|re.MULTILINE),

        r'directive':  re.compile(r'^\s*(?:directive|direct|declare|declaration|decl)\s+([A-z][A-z_0-9]*)\s+(.+)\s*', re.DOTALL|re.MULTILINE),
        r'exec': re.compile(r'^\s*(?:exec|execute)\s+(.*)\s*', re.DOTALL|re.MULTILINE)
    }
    reserved = [r'import', r'import_once', r'inc', r'include', r'require', r'include_once', r'require_once',
                r'if', r'elif', r'else', r'endif', r'fi',
                r'del', r'delete', r'undef', r'remove',
                r'def', r'define', r'macro', r'macros',
                r'directive', r'direct', r'declare', r'declaration', r'decl',
                r'exec', r'execute']
    safe_rx = re.compile(r'eval|__[A-z]+__', re.DOTALL|re.MULTILINE)
    html_parser = HTMLParser()

    def clear():
        IncludeParser.included = []
        IncludeParser.macros = copy.deepcopy(IncludeParser.standartd_macros)
        IncludeParser.declaraions = {}
        IncludeParser.start_ends = set()
        IncludeParser.excludes = set()
        IncludeParser.excludes_tokens = set()
        IncludeParser.excludes_states = []
        IncludeParser.tokens = set()
        IncludeParser.state_table = []
    clear = staticmethod(clear)

    def bracketParse(s, tokens, states, start = True, reduce = True):
        local = { r'count' : 0, r'st_func' : lazy.lazy_stateTable(states) }
        def args(val, state):
            state = local[r'st_func'](val, state)
            if state == r'none':
                if start:
                    if val == r'(':
                        local[r'count'] += 1
                        return r'in_args'
            elif state == r'in_args':
                if val == r'(':
                    local[r'count'] += 1
                elif val == r')':
                    local[r'count'] -= 1
                if local[r'count'] == 0:
                    return r'none'
            return state
            
        stateParse = lazy.lazy(lazy.lazy_tokenize(s, tokens))
        stateParse.group(args, lambda a, v, s : a + v, '')
        if reduce:
            return stateParse.reduce(lambda x, y : x + [y], [])
        return stateParse
    bracketParse = staticmethod(bracketParse)

    def argsParse(s):
        return IncludeParser.bracketParse(s, IncludeParser.string_tokens, IncludeParser.string_states)
    argsParse = staticmethod(argsParse)

    def createSafeEnv():
        return SafeExecuteRecurseLocals(IncludeParser.macros, IncludeParser.access_eval)
    createSafeEnv = staticmethod(createSafeEnv)

    def toString(obj):
        if isinstance(obj, str) or isinstance(obj, six.string_types):
            return obj
        return str(obj)
    toString = staticmethod(toString)

    def no_safe_exec(cmd):
        code = compile(cmd, r'<script>', r'exec')
        env = ExecEnv(IncludeParser.macros, IncludeParser.access_exec)
        exec(code, env.get_globals(), env.get_locals())
        env.write_globals()
    no_safe_exec = staticmethod(no_safe_exec)

    def safe_eval(cmd, loc = None):
        if loc == None:
            loc = IncludeParser.createSafeEnv()
        cmd = re.sub(IncludeParser.safe_rx, r'', cmd)
        code = compile(cmd, r'<script>', r'eval')
        return eval(code, loc.get_globals(), loc.get_locals())
    safe_eval = staticmethod(safe_eval)

    def safe_bool_eval(cmd, loc = None):
        if loc == None:
            loc = IncludeParser.createSafeEnv()
        try:
            return bool(IncludeParser.safe_eval(cmd, loc))
        except:
            print(r'Wrong if expressin')
        return False
    safe_bool_eval = staticmethod(safe_bool_eval)

    def replaceMaros(data, loc=None):
        data = IncludeParser.toString(data)
        if len(data) <= 0:
            return data
        if len(data.strip()) <= 0:
            return data

        if loc == None:
            loc = IncludeParser.createSafeEnv()
        keys = loc.keys()

        tokens = copy.deepcopy(IncludeParser.excludes_tokens)
        tokens.update(IncludeParser.string_tokens)
        tokens.update([x + r'(' for x in keys])

        states = copy.deepcopy(IncludeParser.excludes_states)
        states += IncludeParser.string_states
        states += [[x + r'(', { r'none' : r'in_args' }] for x in keys]

        rx = re.compile(r'(?:^|(?<=\W))(' + r'|'.join(keys) + r')(?=\W|$)', re.DOTALL|re.MULTILINE)
        data = IncludeParser.bracketParse(data, tokens, states, False, True)
        out = r''
        for part in data:
            if len(part.strip()) <= 0:
                out += part
                continue
            bIsFunctional = False
            for fmacro in keys:
                if part.startswith(fmacro + r'('):
                    value = loc[fmacro]
                    if callable(value):
                        try:
                            out += IncludeParser.toString(IncludeParser.safe_eval(part, loc))
                        except:
                            out += part
                    else:
                        out += IncludeParser.toString(value) + IncludeParser.replaceMaros(part[len(fmacro):])
                    bIsFunctional = True
                    break
            bIsExclude = False
            for s, e in IncludeParser.excludes:
                if part.startswith(s) and part.endswith(e):
                    bIsExclude = True
                    out += part
                    break
            if not bIsFunctional and not bIsExclude:
                start = 0
                end = 0
                for m in re.finditer(rx, part):
                    end = m.start()
                    if start < end:
                        out += m.string[start:end]
                    macros_name = m.group(1)
                    if macros_name != None:
                        value = loc[macros_name]
                        if value == None or callable(value):
                            out += m.string[m.start():m.end()]
                        else:
                            out += IncludeParser.toString(value)
                    start = m.end()
                if end != 0:
                    if len(part) - start > 0:
                        out += part[start:]
                if end == 0:
                    out += part
        return out
    replaceMaros = staticmethod(replaceMaros)

    def concat_strings(accum, v):
        for token in IncludeParser.string_tokens:
            if v.startswith(token) and v.endswith(token):
                tlen = len(token)
                return accum + v[tlen:-tlen]

        v = v.split(r'.')
        for part in v:
            if part in IncludeParser.macros:
                val = IncludeParser.macros[part]
                if not isinstance(val, str) and not isinstance(val, six.string_types):
                    continue
                bFind = False
                for token in IncludeParser.string_tokens:
                    if v.startswith(token) and v.endswith(token):
                        tlen = len(token)
                        accum += val[tlen:-tlen]
                        bFind = True
                if bFind == False:
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
            for m in macro_vars:
                env = ExecEnv(IncludeParser.macros)
                if not env.chack_var_name(m):
                    continue
                value = macro_vars[m]
                if value == None:
                    value = 1
                IncludeParser.macros[m] = value
        if len(IncludeParser.start_ends) <= 0 and len(start_ends) > 0:
            IncludeParser.start_ends = start_ends
            for s, e in IncludeParser.start_ends:
                IncludeParser.tokens.add(s)
                IncludeParser.tokens.add(e)
                IncludeParser.tokens.add('\\' + s)
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
                    IncludeParser.excludes_tokens.add(s)
                    IncludeParser.excludes_tokens.add(e)
                    if len(s) == 1:
                        IncludeParser.tokens.add('\\' + s)
                        IncludeParser.excludes_tokens.add('\\' + s)
                    if len(e) == 1:
                        IncludeParser.tokens.add('\\' + e)
                        IncludeParser.excludes_tokens.add('\\' + e)
                    if s == e:
                        IncludeParser.state_table.append([s, { r'none' : s + s, s + s : r'none' }])
                        IncludeParser.excludes_states.append([s, { r'none' : s + s, s + s : r'none' }])
                    else:
                        IncludeParser.state_table.append([s, { r'none' : s + e }])
                        IncludeParser.state_table.append([e, { s + e : r'none' }])
                        IncludeParser.excludes_states.append([s, { r'none' : s + e }])
                        IncludeParser.excludes_states.append([e, { s + e : r'none' }])
    
    def parse(self, data):
        tokenized = lazy.lazy_tokenize(data, IncludeParser.tokens)
        stateParse = lazy.lazy(tokenized)
        stateParse.group(lazy.lazy_stateTable(IncludeParser.state_table), lambda a, v, s : a + v, '')

        local = { r'out' : r'', r'skip' : False, r'tokens' : r'' }
        parent = self
        def calculate(token):
            command = False
            if token != False:
                for s, e in IncludeParser.start_ends:
                    if token.startswith(s) and token.endswith(e):
                        command = token[len(s):-len(e)]
                        if len(command) < 1:
                            command = False
                        break
            
            if command != False or token == False:
                local[r'out'] += IncludeParser.replaceMaros(local[r'tokens'])
                local[r'tokens'] = r''
                if command == False:
                    return
            else:
                if not local[r'skip']:
                    local[r'tokens'] += token
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
        calculate(False)
        return local[r'out']
    
    def pathParser(self, path):
        stateParse = lazy.lazy(lazy.lazy_tokenize(path, IncludeParser.string_tokens))
        stateParse.group(lazy.lazy_stateTable(IncludeParser.string_states), lambda a, v, s : a + v, '')
        path = stateParse.reduce(lambda x, y : IncludeParser.concat_strings(x, y), r'')
        path = self.convertPath(path)
        if not os.path.isabs(path):
            path = os.path.join(self.root, path)
        return path
    
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
            
            ret = IncludeParser.commands[cmd].match(code)
            if ret == None or ret.start() != 0:
                continue
            
            if cmd == r'include':
                keyword, full_path, count = ret.groups()
                if keyword != None and keyword.endswith(r'_once'):
                    count = r'once'
                if count == None:
                    count = 1
                if full_path == None:
                    return False
                path = self.pathParser(full_path)

                out = r''
                names = glob.glob(path)
                for name in names:
                    out += self.includeFile(name, count)
                return out
            elif cmd == r'define':
                macros, args, value = ret.groups()
                env = ExecEnv(IncludeParser.macros)
                if not env.chack_var_name(macros):
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
            elif cmd == r'exec':
                source = ret.group(1)
                if source == None:
                    return False
                
                if len(source) > 0:
                    try:
                        with stdoutIO() as s:
                            IncludeParser.no_safe_exec(source)
                        return s.getvalue()
                    except:
                        path = self.pathParser(source)
                        if not os.path.exists(path):
                            return False    
                        try:
                            with stdoutIO() as s:
                                with codecs.open(path, r'r', self.encoding) as f:
                                    IncludeParser.no_safe_exec( f.read())
                            return s.getvalue()
                        except:
                            return False
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