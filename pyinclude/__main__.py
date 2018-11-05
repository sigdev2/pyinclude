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

import argparse
import re
import os
import json
import glob
import sys
import codecs
from six import string_types

from .pyinclude import include
from . import __name__ as __base_name__, __version__, __desc__, __copyright__

class StandartArguments(argparse.ArgumentParser):
    class Options:
        def __init__(self, **entries):
            self.__dict__.update(entries)
        def __setitem__(self, key, value):
            self.__dict__.update({ key : value})
        def __getitem__(self, key):
            if key in self.__dict__:
                return self.__dict__[key]
            return None
        def get(self, key, d):
            if key in self.__dict__ and self.__dict__[key] != None:
                return self.__dict__[key]
            return d

    __rx_words = re.compile(r'\W', re.M or re.S) 

    def __init__(self, module, default = [r'version', r'encoding', r'quiet']):
        info = module.__name__ + r' ' + module.__version__ + r' ' + module.__copyright__
        super(StandartArguments, self).__init__(prog=module.__name__, description=module.__desc__, epilog=info)
        self.defaults = default

        self.quiet = False
        self.encoding = r'utf-8'

        if r'version' in self.defaults:
            self.add_argument(r'--version', r'-v', action=r'version', version=info)
        if r'encoding' in self.defaults:
            self.add_argument(r'--encoding', r'--charset', r'-ch', r'-scs', nargs=r'?', type=self.check_encoding, default=r'utf-8', help=r'Work files encoding')
        if r'quiet' in self.defaults:
            self.add_argument(r'--quiet', r'-q', nargs=r'?', type=bool, default=False, help = r'No questions')
        
        self.__to_join = []
        self.__to_join_append = []
        self.__to_map = {}
        self.__files_check = []
        self.__defs = []
    
    def add(self, *args, **kwargs):
        self.add_argument(*args, **kwargs)
        name = re.sub(StandartArguments.__rx_words, r'_', args[0].lstrip(self.prefix_chars))
        if r'nargs' in kwargs and kwargs.get(r'nargs') == r'+':
            if kwargs.get(r'action') == r'append':
                self.__to_join.append(name)
            else:
                self.__to_join_append.append(name)
        if r'type' in kwargs and kwargs.get(r'type') in string_types or kwargs.get(r'type') != int:
            self.__to_map[name] = kwargs.get(r'type')
        return self
    
    def add_flag(self, name, short, desc, default=False):
        self.add_argument(name, short, nargs=r'?', type=bool, default=default, help=desc)
        return self
    
    def add_str(self, name, short, desc, default=None, t=str, metavar=r'STR'):
        self.add_argument(name, short, nargs=r'+', type=str, default=default, metavar=metavar, help=desc)
        name = re.sub(StandartArguments.__rx_words, r'_', name.lstrip(self.prefix_chars))
        self.__to_join.append(name)
        if t in string_types:
            self.__to_map[name] = t
        return self

    def add_int(self, name, short, desc, default=None, t=int, metavar=r'NUMBER'):
        self.add_argument(name, short, type=int, default=default, metavar=metavar, help=desc)
        if t != int:
            name = re.sub(StandartArguments.__rx_words, r'_', name.lstrip(self.prefix_chars))
            self.__to_map[name] = t
        return self

    def add_list(self, name, short, desc, t=str, metavar=r'ITEM'):
        self.add_argument(name, short, nargs=r'+', type=str, action=r'append', help=desc)
        name = re.sub(StandartArguments.__rx_words, r'_', name.lstrip(self.prefix_chars))
        self.__to_join_append.append(name)
        if t in string_types or t != int:
            self.__to_map[name] = t
        return self

    def add_pair(self, name, short, desc, is_append=False, t=None, metavar=(r'FIRST', r'SECOND')):
        self.add_argument(name, short, nargs=2, action=(r'append' if is_append else None), metavar=metavar, help=desc)
        if t != None:
            name = re.sub(StandartArguments.__rx_words, r'_', name.lstrip(self.prefix_chars))
            self.__to_map[name] = t
        return self

    def add_file(self, name, short, desc, is_append=False, mask=False, exists=False, metavar=r'FILE'):
        checker = str
        if exists:
            checker = self.exists_file
        else:
            checker = self.no_exists_file

        if mask:
            exists=True
            is_append=True
            checker = self.file_mask

        self.add_argument(name, short, type=checker, action=(r'append' if is_append else None), metavar=metavar, help=desc)
        if not exists:
            name = re.sub(StandartArguments.__rx_words, r'_', name.lstrip(self.prefix_chars))
            self.__files_check.append(name)
        return self
    
    def add_def(self, name, short, desc):
        self.add_argument(name, short, nargs=r'+', action=r'append', type=str, metavar=r'VARS', help=desc)
        name = re.sub(StandartArguments.__rx_words, r'_', name.lstrip(self.prefix_chars))
        self.__to_join_append.append(name)
        self.__to_map[name] = lambda x : self.is_define(x, self.encoding)
        self.__defs.append(name)
    
    def file_mask(self, string):
        if os.path.exists(string):
            return [string]
        names = glob.glob(string)
        if len(names) > 0:
            return names
        raise argparse.ArgumentTypeError('Files \'%r\' not exists' % string)
    
    def exists_file(self, string):
        if os.path.exists(string):
            return string
        raise argparse.ArgumentTypeError('File \'%r\' not exists' % string)
    
    def no_exists_file(self, string):
        if os.path.exists(string):
            if not self.quiet and not self.query_yes_no('Do you want to overwrite file \'%r\'?' % string):
                raise argparse.ArgumentTypeError('File \'%r\' is exists' % string)
        return string

    def parse_args(self, args):
        if r'encoding' in self.defaults:
            arg = self.get_from_args(args, [r'--encoding', r'--charset', r'-ch', r'-scs'], self.check_encoding)
            if arg[1] != None:
                self.encoding = arg[1]
        if r'quiet' in self.defaults:
            arg = self.get_from_args(args, [r'--quiet', r'-q'])
            if arg[1]:
                self.quiet = arg[1]

        opt = vars(super(StandartArguments, self).parse_args(args))
        opt = StandartArguments.Options(**opt)
        for n in self.__to_join:
            opt[n] = self.join_nargs(opt[n])
        for n in self.__to_join_append:
            opt[n] = self.join_nargs(opt[n], True)
        for n in self.__to_map.keys():
            opt[n] = self.check_nrags(opt[n], self.__to_map[n])
        for n in self.__defs:
            d = {}
            for i in opt[n]:
                d.update(i)
            opt[n] = d
        return opt

    def get_from_args(self, args, key, value = False):
        if value == False:
            if isinstance(key, list):
                for k in key:
                    if key in args:
                        return (key, True)
                return (key, False)
            else:
                return (key, key in args)

        i = -1
        if isinstance(key, list):
            for k in key:
                if key in args:
                    i = args.index(key)
                    break
        else:
            if key in args:
                i = args.index(key)
        
        if i < 0:
            return (key, None)
        if i + 1 >= len(args):
            raise argparse.ArgumentTypeError('No value for argument \'%r\'' % key)
        return (key, value(args[i + 1]))

    def check_nrags(self, arr, f):
        if isinstance(arr, list):
            n = []
            for i in arr:
                n.append(f(i))
            return n
        return f(arr)

    def join_nargs(self, arg, is_append = False, sep = r' '):
        if not isinstance(arg, list):
            if is_append:
                return []
            else:
                return None

        if is_append:
            n = []
            for a in arg:
                if isinstance(a, list):
                    n.append(sep.join(a))
                else:
                    n.append(a)
            return n
        return sep.join(arg)

    def check_encoding(self, enc):
        try:
            codecs.lookup(enc)
            return enc
        except LookupError as e:
            raise argparse.ArgumentTypeError('\'%r\' incorect encoding: \'%r\'' % enc, str(e))
    
    def query_yes_no(self, question, default=r'yes'):
        valid = { r'yes': True, r'y': True, r'ye': True,
                  r'no': False, r'n': False }
        if default is None:
            prompt = r' [y/n] '
        elif default == r'yes':
            prompt = r' [Y/n] '
        elif default == r'no':
            prompt = r' [y/N] '
        else:
            raise argparse.ArgumentTypeError('invalid default answer: \'%s\'' % default)

        while True:
            sys.stdout.write(question + prompt)
            choice = sys.stdin.readline().lower()
            if default is not None and choice == r'':
                return valid[default]
            elif choice in valid:
                return valid[choice]
            else:
                sys.stdout.write('Please respond with \'yes\' or \'no\' (or \'y\' or \'n\').\n')
    
    def is_define(self, string, encoding=r'utf-8', from_file = False):
        names = glob.glob(string)
        if len(names) > 0:
            ret = []
            for name in names:
                with codecs.open(name, encoding=encoding) as f:
                    try:
                        json_object = json.loads(f.read(), encoding=encoding)
                        ret.append(json_object)
                    except ValueError as e:
                        try:
                            ret.append(self.is_define(f.read(), encoding, True))
                        except argparse.ArgumentTypeError as e:
                            raise argparse.ArgumentTypeError('\'%r\' incorect vars file: \'%r\'' % string, str(e))
            return ret

        if string.startswith(r'{') and string.endswith(r'}'):
            try:
                if from_file:
                    json_object = json.loads(string, encoding=encoding)
                else:
                    json_object = json.loads(string)
                return json_object
            except ValueError as e:
                argparse.ArgumentTypeError('\'%r\' incorect json: \'%r\'' % string, str(e))

        out = {}
        for m in re.finditer(r'([A-z][A-z0-9]*)(?:\=(?:([A-z_0-9]+)|\'([^\']*)\'|\"([^\"]*)\"))?', string, re.MULTILINE):
            if m == None:
                raise argparse.ArgumentTypeError('\'%r\' is not a var define' % m.string)
            name, text, quoted, dquoted = m.groups()
            val = text
            if val == None:
                val = quoted
            if val == None:
                val = dquoted
            if val == None:
                val = 1
            out[name] = val

        return out

    def _get_action_from_name(self, name):
        container = self._actions
        if name is None:
            return None
        for action in container:
            if r'/'.join(action.option_strings) == name:
                return action
            elif action.metavar == name:
                return action
            elif action.dest == name:
                return action

    def error(self, message):
        exc = sys.exc_info()[1]
        if exc:
            exc.argument = self._get_action_from_name(exc.argument_name)
            raise exc
        super(StandartArguments, self).error(message)

def main(args):

    class Module:
        __name__ = __base_name__
        __version__ = __version__
        __desc__ = __desc__
        __copyright__ = __copyright__
    Module.__name__ = __base_name__

    parser = StandartArguments(Module)

    parser.add(r'input', type=parser.exists_file, metavar=r'FILE', help=r'Enter point preprocessor FILE')
    parser.add_file(r'--out', r'-o', r'Out file')
    parser.add_pair(r'--start_end', r'-se', r'Start and end of used blocks', is_append=True, metavar=(r'START', r'END'))
    parser.add_pair(r'--exclude_start_end', r'-ese', r'Start and end of excluded blocks', is_append=True, metavar=(r'START', r'END'))
    parser.add_def(r'--definition', r'-D', r'Add macros')

    args = parser.parse_args(args)

    if not args.start_end:
        args.start_end = [(r'/*py', r'*/')]
    if not args.exclude_start_end:
        args.exclude_start_end = [('\'', '\''), (r'"', r'"'), (r'"""', r'"""'), ('\'\'\'', '\'\'\''), (r'/*', r'*/'), (r'//', '\n'), (r'#', '\n')]

    out = include(args.input, args.start_end, args.exclude_start_end, args.definition, parser.encoding)
    if args.out:
        with codecs.open(args.out, r'w', encoding=parser.encoding) as f:
            f.write(out)
    else:
        print(out)
    return 0

if __name__ == r'__main__':
    sys.exit(main(sys.argv[1:]))