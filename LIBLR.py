#! /usr/bin/env python
# -*- coding: utf-8 -*-
#  vim: set ts=4 sw=4 tw=0 et :
#======================================================================
#
# LIBLR.py - Parser Generator with LR(1) and LALR
#
# History of this file:
#
#   2023.01.20  skywind  create this file
#   2023.01.21  skywind  grammar analayzer
#   2023.01.22  skywind  basic tokenizer
#   2023.01.23  skywind  grammar loader
#
#======================================================================
from __future__ import unicode_literals, print_function
import sys
import os
import time
import json
import copy
import re
import collections


#----------------------------------------------------------------------
# exports
#----------------------------------------------------------------------
__all__ = ['GrammarError', 'Symbol', 'Vector', 'Production', 'Grammar']


#----------------------------------------------------------------------
# logs
#----------------------------------------------------------------------
LOG_ERROR = lambda *args: print('error:', *args)
LOG_WARNING = lambda *args: print('warning:', *args)
LOG_INFO = lambda *args: print('info:', *args)
LOG_DEBUG = lambda *args: print('debug:', *args)


#----------------------------------------------------------------------
# GrammarError
#----------------------------------------------------------------------
class GrammarError (Exception):
    pass


#----------------------------------------------------------------------
# 符号类：包括终结符和非终结符，term 代表是否为终结符，
# 空的话用空字符串表示
#----------------------------------------------------------------------
class Symbol (object):

    def __init__ (self, name, terminal = False):
        self.name = name
        self.term = terminal
    
    # 转为可打印字符串
    def __str__ (self):
        if not self.name:
            return "''"
        return self.name

    # 判断是否相等
    def __eq__ (self, symbol):
        if isinstance(symbol, str):
            return (self.name == symbol)
        elif symbol is None:
            return (self is None)
        elif not isinstance(symbol, Symbol):
            raise TypeError('Symbol cannot be compared to a %s'%type(symbol))
        return (self.name == symbol.name)

    def __ne__ (self, symbol):
        return (not (self == symbol))

    # >=
    def __ge__ (self, symbol):
        return (self.name >= symbol.name)

    # > 
    def __gt__ (self, symbol):
        return (self.name > symbol.name)

    # <=
    def __le__ (self, symbol):
        return (self.name <= symbol.name)

    # < 
    def __lt__ (self, symbol):
        return (self.name < symbol.name)

    def __repr__ (self):
        if not self.term:
            return '%s(%r)'%(type(self).__name__, self.name)
        return '%s(%r, %r)'%(type(self).__name__, self.name, self.term)

    # 求哈希，有这个函数可以将 Symbol 放到容器里当 key
    def __hash__ (self):
        return hash(self.name)

    # 拷贝
    def __copy__ (self):
        obj = Symbol(self.name, self.term)
        if hasattr(self, 'value'):
            obj.value = self.value
        if hasattr(self, 'token'):
            obj.token = self.token
        return obj

    # 深度拷贝
    def __deepcopy__ (self):
        obj = Symbol(self.name, self.term)
        if hasattr(self, 'value'):
            obj.value = copy.deepcopy(self.value)
        if hasattr(self, 'token'):
            obj.token = copy.deepcopy(self.token)
        return obj

    # 判断是否是字符串字面量
    def _is_literal (self):
        if len(self.name) < 2:
            return False
        mark = self.name[0]
        if mark not in ('"', "'"):
            return False
        if self.name[-1] == mark:
            return True
        return False

    # 判断是否是空/epsilon
    @property
    def is_epsilon (self):
        if self.term:
            return False
        elif self.name == '':
            return True
        if self.name in ('%empty', '%e', '%epsilon', '\u03b5', '<empty>'):
            return True
        return False

    # 判断是否是字符串字面量
    @property
    def is_literal (self):
        return self._is_literal()


#----------------------------------------------------------------------
# 从字符串或者 tuple 创建一个 Symbol
#----------------------------------------------------------------------
def load_symbol (source):
    if isinstance(source, Symbol):
        return source
    elif isinstance(source, str):
        sym = Symbol(source)
        if sym.is_literal:
            sym.term = True
            if len(sym.name) == 2 and sym.name[0] == sym.name[1]:
                sym.term = False
                sym.name = ''
            try: sym.value = eval(sym.name)
            except: pass
        elif source == '$':
            sym.term = True
        elif source == '#':
            sym.term = True
        return sym
    elif isinstance(source, list) or isinstance(source, tuple):
        assert len(source) > 0
        if len(source) == 0:
            raise ValueError('bad symbol: %r'%source)
        elif len(source) == 1:
            return Symbol(source[0])
        elif len(source) == 2:
            return Symbol(source[0], source[1])
        s = Symbol(source[0], source[1])
        s.value = source[2]
        return s
    raise ValueError('bad symbol: %r'%source)


#----------------------------------------------------------------------
# 符号矢量：符号列表
#----------------------------------------------------------------------
class Vector (object):

    def __init__ (self, vector):
        self.m = tuple(self.__load_vector(vector))
        self.__hash = None

    def __load_vector (self, vector):
        epsilon = True
        output = []
        p = [ load_symbol(n) for n in vector ]
        for symbol in p:
            if not symbol.is_epsilon:
                epsilon = False
                break
        if not epsilon:
            for n in p:
                if not n.is_epsilon:
                    output.append(n)
        return output

    def __len__ (self):
        return len(self.m)

    def __getitem__ (self, index):
        return self.m[index]

    def __contains__ (self, key):
        if isinstance(key, int):
            return (key >= 0 and key < len(self.m))
        for n in self.m:
            if n == key:
                return True
        return False

    def __hash__ (self):
        if self.__hash is None:
            h = tuple([n.name for n in self.m])
            self.__hash = hash(h)
        return self.__hash

    def __iter__ (self):
        return self.m.__iter__()

    def __repr__ (self):
        return '%s(%r)'%(type(self).__name__, self.m)

    def __str__ (self):
        body = [ str(n) for n in self.m ]
        return ' '.join(body)

    def __eq__ (self, p):
        assert isinstance(p, Vector)
        if hash(self) != hash(p):
            return False
        return (self.m == p.m)

    def __ne__ (self, p):
        return (not (self == p))

    def __ge__ (self, p):
        return (self.m >= p.m)

    def __gt__ (self, p):
        return (self.m > p.m)

    def __le__ (self, p):
        return (self.m <= p.m)

    def __lt__ (self, p):
        return (self.m < p.m)

    def __copy__ (self):
        obj = Vector(self.m)
        obj.__hash = self.__hash
        return obj

    def __deepcopy__ (self):
        p = [ n.__deepcopy__() for n in self.m ]
        obj = Vector(p)
        obj.__hash = self.__hash
        return obj

    def search (self, symbol, stop = -1):
        if stop < 0:
            return self.m.index(symbol)
        return self.m.index(symbol, stop)

    @property
    def is_empty (self):
        return (len(self.m) == 0)

    # 计算最左边的终结符
    def leftmost_terminal (self):
        for n in self.m:
            if n.term:
                return n
        return None

    # 计算最右边的终结符
    def rightmost_terminal (self):
        index = len(self.m) - 1
        while index >= 0:
            symbol = self.m[index]
            if symbol.term:
                return symbol
            index -= 1
        return None


#----------------------------------------------------------------------
# 产生式/生成式：由 head -> body 组成，head 是 symbol，
# budy 是一个 Vector，即 symbol 组成的序列
#----------------------------------------------------------------------
class Production (object):

    def __init__ (self, head, body, index = -1):
        self.head = load_symbol(head)
        self.body = Vector(body)
        self.__hash = None
        self.index = index
        self.is_epsilon = None
        self.has_epsilon = None
        self.precedence = None
        self.action = None

    def __len__ (self):
        return len(self.body)

    def __getitem__ (self, index):
        return self.body[index]

    def __contains__ (self, key):
        return (key in self.body)

    def __hash__ (self):
        if self.__hash is None:
            h1 = hash(self.head)
            h2 = hash(self.body)
            self.__hash = hash((h1, h2))
        return self.__hash

    def __iter__ (self):
        return self.body.__iter__()

    def __repr__ (self):
        return '%s(%r, %r)'%(type(self).__name__, self.head, self.body)

    def __str__ (self):
        body = [ str(n) for n in self.body ]
        return '%s: %s ;'%(self.head, ' '.join(body))

    def __eq__ (self, p):
        assert isinstance(p, Production)
        if hash(self) != hash(p):
            return False
        if self.head != p.head:
            return False
        return (self.body == p.body)

    def __ne__ (self, p):
        return not (self == p)

    def __ge__ (self, p):
        if self.head > p.head: 
            return True
        elif self.head < p.head:
            return False
        return (self.body >= p.body)

    def __gt__ (self, p):
        if self.head > p.head:
            return True
        elif self.head < p.head:
            return False
        return (self.body > p.body)

    def __lt__ (self, p):
        return (not (self >= p))

    def __le__ (self, p):
        return (not (self > p))

    def __copy__ (self):
        obj = Production(self.head, self.body)
        obj.index = self.index
        obj.precedence = self.precedence
        obj.is_epsilon = self.is_epsilon
        obj.has_epsilon = self.has_epsilon
        obj.__hash = self.__hash
        obj.action = self.action
        return obj

    def __deepcopy__ (self):
        p = self.body.__deepcopy__()
        obj = Production(self.head.__deepcopy__(), p)
        obj.index = self.index
        obj.precedence = self.precedence
        obj.is_epsilon = self.is_epsilon
        obj.has_epsilon = self.has_epsilon
        obj.__hash = self.__hash
        if self.action:
            obj.action = copy.deepcopy(self.action)
        return obj

    def search (self, symbol, stop = -1):
        return self.body.search(symbol, stop)

    @property
    def is_empty (self):
        return (len(self.body) == 0)

    # 计算最右边的终结符
    def rightmost_terminal (self):
        return self.body.rightmost_terminal()

    # 最左侧的终结符
    def leftmost_terminal (self):
        return self.body.leftmost_terminal()

    # 计算是否直接左递归
    @property
    def is_left_recursion (self):
        if len(self.body) == 0:
            return False
        return (self.head == self.body[0])

    # 计算是否直接右递归
    @property
    def is_right_recursion (self):
        if len(self.body) == 0:
            return False
        return (self.head == self.body[-1])

    def __action_to_string (self, m):
        if isinstance(m, str):
            return m
        assert isinstance(m, tuple)
        name:str = m[0]
        stack = m[1]
        if name.startswith('{') and name.endswith('}'):
            return '{%s/%d}'%(name[1:-1], stack)
        return '%s/%d'%(name, stack)

    # 返回包含动作的身体部分
    def stringify (self, head = True, body = True, action = False, prec = False):
        text = ''
        if head:
            text += str(self.head) + ': '
        act = getattr(self, 'action', {})
        if body:
            for i, n in enumerate(self.body.m):
                if action and act and (i in act):
                    for m in act[i]:
                        text += '%s '%self.__action_to_string(m)
                text += n.name + ' '
            i = len(self.body)
            if action and act and (i in act):
                for m in act[i]:
                    text += '%s '%self.__action_to_string(m)
        if prec:
            text += ' <%s>'%(self.precedence, )
        return text.strip('\r\n\t ')



#----------------------------------------------------------------------
# 语法类，一个语法 G 由终结符，非终结符和产生式组成
#----------------------------------------------------------------------
class Grammar (object):

    def __init__ (self):
        self.production = []
        self.symbol = {}            # str -> Symbol map
        self.terminal = {}          # str -> Symbol map
        self.rule = {}              # str -> list
        self.precedence = {}        # str -> prec
        self.assoc = {}             # str -> one of (None, 'left', 'right')
        self._anchor = {}           # str -> (filename, linenum)
        self._dirty = False
        self.scanner = []           # scanner rules
        self.start = None

    def reset (self):
        self.production.clear()
        self.symbol.clear()
        self.terminal.clear()
        self.nonterminal.clear()
        self.rule.clear()
        self._anchor.clear()
        self.scanner.clear()
        self.start = None
        return 0

    def _symbol_name (self, symbol):
        if isinstance(symbol, Symbol):
            return symbol.name
        elif isinstance(symbol, str):
            return symbol
        raise TypeError('bad symbol: %r'%symbol)

    def __len__ (self):
        return len(self.production)

    def __getitem__ (self, index):
        return self.production[index]

    def __iter__ (self):
        return self.production.__iter__()

    def __contains__ (self, key):
        if isinstance(key, int):
            return (key >= 0 and key < len(self.production))
        elif isinstance(key, Production):
            for p in self.production:
                if p == key:
                    return True
        elif isinstance(key, Symbol):
            return (key.name in self.symbol)
        elif isinstance(key, str):
            return (key in self.symbol)
        return False

    def __copy__ (self):
        obj = Grammar()
        for p in self.production:
            obj.push_precedence(p.__copy__())
        for t in self.terminal:
            obj.push_token(t)
        for p in self.precedence:
            c = self.precedence[p]
            obj.push_precedence(p, c[0], c[1])
        obj.srcinfo = self.srcinfo.__copy__()
        obj.update()
        if self.start:
            obj.start = obj.symbol[self.start.name]
        return obj

    def __deepcopy__ (self):
        obj = Grammar()
        for p in self.production:
            obj.push_precedence(p.__deepcopy__())
        for t in self.terminal:
            obj.push_token(t)
        for p in self.precedence:
            c = self.precedence[p]
            obj.push_precedence(p, c[0], c[1])
        obj.srcinfo = self.srcinfo.__deepcopy__()
        obj.update()
        if self.start:
            obj.start = obj.symbol[self.start.name]
        return obj

    def insert (self, index, production):
        self.production.insert(index, production)
        self._dirty = True

    def search (self, p, stop = -1):
        if stop < 0:
            return self.production.index(p)
        return self.production.index(p, stop)

    def remove (self, index):
        if isinstance(index, int):
            self.production.pop(index)
        else:
            index = self.search(index)
            self.production.pop(index)
        self._dirty = True

    def pop (self, index = -1):
        self.production.pop(index)
        self._dirty = True

    def append (self, production):
        index = len(self.production)
        self.production.append(production)
        production.index = index
        self._dirty = True

    def replace (self, index, source):
        if isinstance(source, Production):
            self.production[index] = source
        elif isinstance(source, list) or isinstance(source, tuple):
            for n in source:
                assert isinstance(n, Production)
                self.production.insert(index + 1, n)
            self.production.pop(index)
        self._dirty = True

    def update (self):
        self.symbol.clear()
        self.rule.clear()
        for i, p in enumerate(self.production):
            p.index = i
            head = p.head
            if head.name not in self.symbol:
                self.symbol[head.name] = head
            for n in p.body:
                if n.name not in self.symbol:
                    self.symbol[n.name] = n
            if head.name not in self.rule:
                self.rule[head.name] = []
            self.rule[head.name].append(p)
        for n in self.terminal:
            s = self.terminal[n]
            if not s.term:
                s.term = True
        for n in self.symbol:
            s = self.symbol[n]
            s.term = (n in self.terminal)
            if not s.term:
                if s.name not in self.rule:
                    self.rule[s.name] = []
        for p in self.production:
            p.head.term = (p.head.name in self.terminal)
            for n in p.body:
                n.term = (n.name in self.terminal)
        for p in self.production:
            if p.precedence is None:
                rightmost = p.rightmost_terminal()
                if rightmost and (rightmost in self.precedence):
                    p.precedence = self.precedence[rightmost]
        self._dirty = False
        return 0

    # declare terminal
    def push_token (self, token):
        name = self._symbol_name(token)
        if token not in self.terminal:
            t = load_symbol(token)
            t.term = True
            self.terminal[name] = t
        self._dirty = True
        return 0

    # push precedence
    def push_precedence (self, symbol, prec, assoc):
        name = self._symbol_name(symbol)
        self.precedence[name] = prec
        self.assoc[name] = assoc

    # push scanner (aka. lexer) rules
    def push_scanner (self, obj):
        self.scanner.append(obj)
        return 0

    # create new symbol according to self.terminal
    def create_symbol (self, name):
        cc = load_symbol(name)
        if name != '':
            if name in self.terminal:
                cc.term = True
        return cc

    # argument
    def argument (self):
        if not self.start:
            raise GrammarError('no start point')
        if 'S^' in self.symbol:
            raise GrammarError('already argumented')
        head = 'S^'
        p = Production(head, [self.start])
        self.insert(0, p)
        self.start = p.head
        self.update()
        return 0

    def __anchor_key (self, obj):
        if isinstance(obj, str):
            return obj
        elif isinstance(obj, Symbol):
            return str(obj)
        elif isinstance(obj, int):
            return '^INT/' + str(obj)
        elif isinstance(obj, Vector):
            return '^VEC/' + str(obj)
        elif isinstance(obj, Production):
            return '^PROD/' + str(obj)
        return str(obj)

    # anchor: source file info (filename, line_num)
    def anchor_set (self, obj, filename, line_num):
        self._anchor[self.__anchor_key(obj)] = (filename, line_num)
        return 0

    def anchor_get (self, obj):
        key = self.__anchor_key(obj)
        if key not in self._anchor:
            return (None, None)
        return self._anchor[key]

    def anchor_has (self, obj):
        key = self.__anchor_key(obj)
        return (key in self._anchor)

    def print (self, mode = 0, action = False, prec = False):
        if mode == 0:
            for i, n in enumerate(self.production):
                t = '(%d) %s'%(i, n.stringify(True, True, action, prec))
                print(t)
        else:
            keys = list(self.rule.keys())
            for key in keys:
                head = str(key) + ': '
                padding = ' ' * (len(head) - 2)
                for i, p in enumerate(self.rule[key]):
                    if i == 0:
                        print(head, end = '')
                    else:
                        print(padding + '| ', end = '')
                    print(p.stringify(False, True, action, prec), end = ' ')
                    if len(self.rule[key]) > 1:
                        print('')
                if len(self.rule[key]) > 1:
                    print(padding + ';')
                else:
                    print(';')
        return 0

    def __str__ (self):
        text = []
        for i, n in enumerate(self.production):
            t = '(%d) %s'%(i, str(n))
            text.append(t)
        return '\n'.join(text)



#----------------------------------------------------------------------
# marks
#----------------------------------------------------------------------
MARK_UNVISITED = 0
MARK_VISITING = 1
MARK_VISITED = 2

EPSILON = Symbol('', False)
EOF = Symbol('$', True)
PSHARP = Symbol('#', True)



#----------------------------------------------------------------------
# 符号信息
#----------------------------------------------------------------------
class SymbolInfo (object):

    def __init__ (self, symbol):
        self.symbol = symbol
        self.mark = MARK_UNVISITED
        self.rules = []
        self.rule_number = 0
        self.is_epsilon = None
        self.has_epsilon = None

    def __copy__ (self):
        obj = SymbolInfo(self.symbol)
        return obj

    def __deepcopy__ (self):
        return self.__copy__()

    @property
    def is_terminal (self):
        return self.symbol.term

    @property
    def name (self):
        return self.symbol.name

    def reset (self):
        self.mark = MARK_UNVISITED

    def check_epsilon (self):
        if len(self.rules) == 0:
            return 1
        count = 0
        for rule in self.rules:
            if rule.is_epsilon:
                count += 1
        if count == len(rule):
            return 2
        if count > 0:
            return 1
        return 0


#----------------------------------------------------------------------
# analyzer
#----------------------------------------------------------------------
class GrammarAnalyzer (object):

    def __init__ (self, g: Grammar):
        assert g
        self.g = g
        self.info = {}
        self.epsilon = Symbol('')
        self.FIRST = {}
        self.FOLLOW = {}
        self.terminal = {}
        self.nonterminal = {}
        self.verbose = 2

    def process (self, expand_action = True):
        if expand_action:
            self.__argument_semantic_action()
        if self.g._dirty:
            self.g.update()
        self.__build_info()
        self.__update_epsilon()
        self.__update_first_set()
        self.__update_follow_set()
        self.__check_integrity()
        return 0

    def __build_info (self):
        self.info.clear()
        self.terminal.clear()
        self.nonterminal.clear()
        g = self.g
        for name in g.symbol:
            info = SymbolInfo(g.symbol[name])
            self.info[name] = info
            info.reset()
            rules = g.rule.get(name, [])
            info.rule_number = len(rules)
            info.rules = rules
            if info.is_terminal:
                self.terminal[info.name] = info.symbol
            else:
                self.nonterminal[info.name] = info.symbol
        return 0

    def __update_first_set (self):
        self.FIRST.clear()
        for name in self.g.symbol:
            symbol = self.g.symbol[name]
            if symbol.term:
                self.FIRST[name] = set([name])
            else:
                self.FIRST[name] = set()
        self.FIRST['$'] = set(['$'])
        self.FIRST['#'] = set(['#'])
        while 1:
            changes = 0
            for symbol in self.nonterminal:
                info = self.info[symbol]
                for rule in info.rules:
                    first = self.__calculate_first_set(rule.body)
                    for n in first:
                        if n not in self.FIRST[symbol]:
                            self.FIRST[symbol].add(n)
                            changes += 1
            if not changes:
                break
        return 0

    def __calculate_first_set (self, vector):
        output = set([])
        index = 0
        for symbol in vector:
            if symbol.term:
                output.add(symbol.name)
                break
            if symbol.name not in self.FIRST:
                for key in self.FIRST.keys():
                    print('FIRST:', key)
                raise ValueError('FIRST set does not contain %r'%symbol.name)
            for name in self.FIRST[symbol.name]:
                if name != EPSILON:
                    output.add(name)
            if EPSILON not in self.FIRST[symbol.name]:
                break
            index += 1
        if index >= len(vector):
            output.add(EPSILON.name)
        return output

    def __update_follow_set (self):
        self.FOLLOW.clear()
        start = self.g.start
        if not self.g.start:
            if len(self.g) > 0:
                start = self.g[0].head
        if not start:
            internal.echo_error('start point is required')
            return 0
        FOLLOW = self.FOLLOW
        for n in self.nonterminal:
            FOLLOW[n] = set([])
        FOLLOW[start.name] = set(['$'])
        while 1:
            changes = 0
            for p in self.g:
                for i, symbol in enumerate(p.body):
                    if symbol.term:
                        continue
                    follow = p.body[i + 1:]
                    first = self.vector_first_set(follow)
                    epsilon = False
                    for n in first:
                        if n != EPSILON.name:
                            if n not in FOLLOW[symbol.name]:
                                FOLLOW[symbol.name].add(n)
                                changes += 1
                        else:
                            epsilon = True
                    if epsilon or i == len(p.body) - 1:
                        for n in FOLLOW[p.head]:
                            if n not in FOLLOW[symbol.name]:
                                FOLLOW[symbol.name].add(n)
                                changes += 1
            if not changes:
                break
        return 0

    def __update_epsilon (self):
        g = self.g
        for info in self.info.values():
            if info.symbol.term:
                info.is_epsilon = False
                info.has_epsilon = False
                info.mark = MARK_VISITED
            elif len(info.rules) == 0:
                info.is_epsilon = False
                info.has_epsilon = False
                info.mark = MARK_VISITED
            else:
                is_count = 0
                size = len(info.rules)
                for p in info.rules:
                    if p.is_epsilon:
                        is_count += 1
                if is_count >= size:
                    info.is_epsilon = True
                    info.has_epsilon = True
                    info.mark = MARK_VISITED
                elif is_count > 0:
                    info.has_epsilon = True

        while True:
            count = 0
            for p in g.production:
                count += self.__update_epsilon_production(p)
            for info in self.info.values():
                count += self.__update_epsilon_symbol(info)
            if not count:
                break
        return 0

    def __update_epsilon_symbol (self, info: SymbolInfo):
        count = 0
        if info.symbol.term:
            return 0
        elif info.is_epsilon is not None:
            if info.has_epsilon is not None:
                return 0
        is_count = 0
        isnot_count = 0
        has_count = 0
        hasnot_count = 0
        for p in info.rules:
            if p.is_epsilon:
                is_count += 1
            elif p.is_epsilon is not None:
                isnot_count += 1
            if p.has_epsilon:
                has_count += 1
            elif p.has_epsilon is not None:
                hasnot_count += 1
        size = len(info.rules)
        if info.is_epsilon is None:
            if is_count >= size:
                info.is_epsilon = True
                info.has_epsilon = True
                count += 1
            elif isnot_count >= size:
                info.is_epsilon = False
                info.has_epsilon = False
                count += 1
        if info.has_epsilon is None:
            if has_count > 0:
                info.has_epsilon = True
                count += 1
            elif hasnot_count >= size:
                info.has_epsilon = False
                count += 1
        return count

    def __update_epsilon_production (self, p: Production):
        count = 0
        if (p.is_epsilon is not None) and (p.has_epsilon is not None):
            return 0
        if p.leftmost_terminal() is not None:
            if p.is_epsilon is None:
                p.is_epsilon = False
                count += 1
            if p.has_epsilon is None:
                p.has_epsilon = False
                count += 1
            return count
        is_count = 0
        isnot_count = 0
        has_count = 0
        hasnot_count = 0
        for n in p.body:
            info = self.info[n.name]
            if info.is_epsilon:
                is_count += 1
            elif info.is_epsilon is not None:
                isnot_count += 1
            if info.has_epsilon:
                has_count += 1
            elif info.has_epsilon is not None:
                hasnot_count += 1
        if p.is_epsilon is None:
            if is_count >= len(p.body):
                p.is_epsilon = True
                p.has_epsilon = True
                count += 1
            elif isnot_count > 0:
                p.is_epsilon = False
                count += 1
        if p.has_epsilon is None:
            if has_count >= len(p.body):
                p.has_epsilon = True
                count += 1
            elif hasnot_count > 0:
                p.has_epsilon = False
                count += 1
        return count

    def vector_is_epsilon (self, vector: Vector):
        if vector.leftmost_terminal() is not None:
            return False
        is_count = 0
        isnot_count = 0
        for symbol in vector:
            if symbol.name not in self.info:
                continue
            info = self.info[symbol.name]
            if info.is_epsilon:
                is_count += 1
            elif info.is_epsilon is not None:
                isnot_count += 1
        if is_count >= len(vector):
            return True
        return False

    def vector_has_epsilon (self, vector: Vector):
        if vector.leftmost_terminal() is not None:
            return False
        is_count = 0
        isnot_count = 0
        has_count = 0
        hasnot_count = 0
        for symbol in vector:
            if symbol.name not in self.info:
                continue
            info = self.info[symbol.name]
            if info.is_epsilon:
                is_count += 1
            elif info.is_epsilon is not None:
                isnot_count += 1
            if info.has_epsilon:
                has_count += 1
            elif info.has_epsilon is not None:
                hasnot_count += 1
        size = len(vector)
        if (is_count >= size) or (has_count >= size):
            return True
        return False

    def vector_first_set (self, vector):
        return self.__calculate_first_set(vector)

    def __integrity_error (self, *args):
        text = ' '.join(args)
        internal.echo_error('integrity: ' + text)
        return 0

    def symbol_error (self, symbol, *args):
        if self.verbose < 1:
            return 0
        if symbol is None:
            return internal.echo_error(' '.join(args), self.g.file_name, 1)
        return internal.symbol_error(self.g, symbol, *args)

    def symbol_warning (self, symbol, *args):
        if self.verbose < 2:
            return 0
        if symbol is None:
            return internal.echo_warning(' '.join(args), self.g.file_name, 1)
        return internal.symbol_warning(self.g, symbol, *args)

    def __check_integrity (self):
        error = 0
        for info in self.info.values():
            symbol = info.symbol
            if symbol.term:
                continue
            name = symbol.name
            first = self.FIRST[name]
            if EPSILON.name in first:
                if len(first) == 1:
                    if not info.is_epsilon:
                        t = 'symbol %s is not epsilon but '%name
                        t += 'first set only contains epsilon'
                        self.__integrity_error(t)
                        error += 1
                    if not info.has_epsilon:
                        t = 'symbol %s has not epsilon but '%name
                        t += 'first set only contains epsilon'
                        self.__integrity_error(t)
                        error += 1
                elif len(first) > 0:
                    if info.is_epsilon:
                        t = 'symbol %s is epsilon but '%name
                        t += 'first set contains more than epsilon'
                        self.__integrity_error(t)
                        error += 1
                    if not info.has_epsilon:
                        t = 'symbol %s has not epsilon but '%name
                        t += 'first set contains epsilon'
                        self.__integrity_error(t)
                        error += 1
            else:
                if info.is_epsilon:
                    t = 'symbol %s is epsilon but '%name
                    t += 'first set does not contains epsilon'
                    self.__integrity_error(t)
                    error += 1
                if info.has_epsilon:
                    t = 'symbol %s has epsilon but '%name
                    t += 'first set does not contains epsilon'
                    self.__integrity_error(t)
                    error += 1
        if error and 0:
            sys.exit(1)
        return error

    def clear_mark (self, init = MARK_UNVISITED):
        for info in self.info.values():
            info.mark = init
        return 0

    def __iter_child (self, symbol):
        if symbol in self.g.rule:
            for rule in self.g.rule[symbol]:
                for n in rule.body:
                    yield n.name
        return None

    def find_reachable (self, parents):
        output = []
        if parents is None:
            if self.g.start is None:
                return set()
            roots = self.g.start.name
        elif isinstance(parents, str):
            roots = [parents]
        elif isinstance(parents, Symbol):
            roots = [parents.name]
        else:
            roots = parents
        for symbol in internal.bfs(roots, self.__iter_child):
            output.append(symbol)
        return output

    def find_undefined_symbol (self):
        undefined = set([])
        for sname in self.g.symbol:
            if sname in self.g.terminal:
                continue
            if sname not in self.g.rule:
                if sname not in undefined:
                    undefined.add(sname)
            elif len(self.g.rule[sname]) == 0:
                if sname not in undefined:
                    undefined.add(sname)
        return list(undefined)

    def find_terminated_symbol (self):
        terminated = set([])
        for symbol in self.g.symbol.values():
            if symbol.term:
                terminated.add(symbol.name)
        while 1:
            changes = 0
            for symbol in self.g.symbol.values():
                if symbol.name in terminated:
                    continue
                elif symbol.name not in self.g.rule:
                    continue
                for rule in self.g.rule[symbol.name]:
                    can_terminate = True
                    for n in rule.body:
                        if n.name not in terminated:
                            can_terminate = False
                            break
                    if can_terminate:
                        if symbol.name not in terminated:
                            terminated.add(symbol.name)
                            changes += 1
                        break
            if not changes:
                break
        return list(terminated)

    def check_grammar (self):
        self.error = 0
        self.warning = 0
        if len(self.g) == 0:
            self.symbol_error(None, 'no rules has been defined')
            self.error += 1
        for n in self.find_undefined_symbol():
            self.symbol_error(n, 'symbol %r is used, but is not defined as a token and has no rules'%n)
            self.error += 1
        smap = set(self.find_reachable(self.g.start))
        for symbol in self.g.symbol.values():
            if symbol.term:
                continue
            if symbol.name not in smap:
                self.symbol_warning(symbol, 'nonterminal \'%s\' useless in grammar'%symbol)
                self.warning += 1
        if self.g.start:
            if self.g.start.term:
                t = 'start symbol %s is a token'
                self.symbol_error(self.g.start, t)
                self.error += 1
            terminated = self.find_terminated_symbol()
            # print('terminated', terminated)
            if self.g.start.name not in terminated:
                t = 'start symbol %s does not derive any sentence'%self.g.start.name
                self.symbol_error(self.g.start, t)
                self.error += 1
        else:
            self.symbol_error(None, 'start symbol is not defined')
            self.error += 1
        return self.error

    # 将 L 型 SDT （即生成式里有语法动作的）转换为 S 型纯后缀的模式
    def __argument_semantic_action (self):
        rules = []
        anchors = []
        name_id = 1
        for rule in self.g.production:
            rule:Production = rule
            anchor = self.g.anchor_get(rule)
            if not rule.action:
                rules.append(rule)
                anchors.append(anchor)
                continue
            count = 0
            for key in rule.action.keys():
                if key < len(rule):
                    count += 1
            if count == 0:
                rules.append(rule)
                anchors.append(anchor)
                continue
            body = []
            children = []
            for pos, symbol in enumerate(rule.body):
                if pos in rule.action:
                    head = Symbol('M@%d'%name_id, False)
                    name_id += 1
                    child = Production(head, [])
                    child.action = {}
                    child.action[0] = []
                    stack_pos = len(body)
                    for act in rule.action[pos]:
                        child.action[0].append((act[0], stack_pos))
                    child.parent = len(rules)
                    children.append(child)
                    body.append(head)
                    self.g.anchor_set(head, anchor[0], anchor[1])
                body.append(symbol)
            root = Production(rule.head, body)
            root.precedence = rule.precedence
            action = {}
            stack_pos = len(body)
            keys = list(filter(lambda k: k >= len(rule), rule.action.keys()))
            keys.sort()
            # print('keys', keys)
            for key in keys:
                assert key >= len(rule)
                for act in rule.action[key]:
                    if stack_pos not in action:
                        action[stack_pos] = []
                    action[stack_pos].append((act[0], stack_pos))
            if action:
                root.action = action
            rules.append(root)
            anchors.append(anchor)
            for child in children:
                rules.append(child)
                anchors.append(anchor)
                child.parent = root
        self.g.production.clear()
        for pos, rule in enumerate(rules):
            self.g.append(rule)
            anchor = anchors[pos]
            self.g.anchor_set(rule, anchor[0], anchor[1])
        self.g.update()
        return 0

    def set_to_text (self, s):
        t = []
        if len(s) == 0:
            return '{ }'
        for n in s:
            t.append((n == '') and '<empty>' or n)
        return '{ %s }'%(', '.join(t),)

    def print_epsilon (self):
        rows = []
        rows.append(['Symbol', 'Is Epsilon', 'Has Epsilon'])
        for info in self.info.values():
            eis = info.is_epsilon and 1 or 0
            ehas = info.has_epsilon and 1 or 0
            rows.append([info.name, eis, ehas])
        text = cstring.tabulify(rows, 1)
        print(text)
        print()
        return 0

    def print_first (self):
        rows = []
        rows.append(['Symbol X', 'First[X]', 'Follow[X]'])
        for name in self.nonterminal:
            t1 = self.set_to_text(self.FIRST[name])
            t2 = self.set_to_text(self.FOLLOW[name])
            rows.append([name, t1, t2])
        text = cstring.tabulify(rows, 1)
        print(text)
        print()
        return 0


#----------------------------------------------------------------------
# Token: (name, value, line, column)
# name represents token type, since "type" is a reserved word in 
# python, choose "name" instead
#----------------------------------------------------------------------
class Token (object):

    def __init__ (self, name, value, line = 0, column = 0):
        self.name = name
        self.value = value
        self.line = line
        self.column = column

    def __str__ (self):
        if self.line is None:
            return '(%s, %s)'%(self.name, self.value)
        t = (self.name, self.value, self.line, self.column)
        return '(%s, %s, %s, %s)'%t

    def __repr__ (self):
        n = type(self).__name__
        if self.line is None:
            return '%s(%r, %r)'%(n, self.name, self.value)
        t = (n, self.name, self.value, self.line, self.column)
        return '%s(%r, %r, %r, %r)'%t

    def __copy__ (self):
        return Token(self.name, self.value, self.line, self.column)

    def __deepcopy__ (self):
        return self.__copy__()


#----------------------------------------------------------------------
# tokenize
#----------------------------------------------------------------------
def _tokenize(code, specs, eof = None):
    patterns = []
    definition = {}
    extended = {}
    if not specs:
        return None
    for index in range(len(specs)):
        spec = specs[index]
        name, pattern = spec[:2]
        pn = 'PATTERN%d'%index
        definition[pn] = name
        if len(spec) >= 3:
            extended[pn] = spec[2]
        patterns.append((pn, pattern))
    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in patterns)
    line_starts = []
    pos = 0
    index = 0
    while 1:
        line_starts.append(pos)
        pos = code.find('\n', pos)
        if pos < 0:
            break
        pos += 1
    line_num = 0
    for mo in re.finditer(tok_regex, code):
        kind = mo.lastgroup
        value = mo.group()
        start = mo.start()
        while line_num < len(line_starts) - 1:
            if line_starts[line_num + 1] > start:
                break
            line_num += 1
        line_start = line_starts[line_num]
        name = definition[kind]
        if name is None:
            continue
        elif callable(name):
            if kind not in extended:
                obj = name(value)
            else:
                obj = name(value, extended[kind])
            name, value = None, None
            if isinstance(obj, list) or isinstance(obj, tuple):
                if len(obj) > 0: 
                    name = obj[0]
                if len(obj) > 1:
                    value = obj[1]
            else:
                name = obj
        yield (name, value, line_num + 1, start - line_start + 1)
    if eof is not None:
        line_start = line_starts[-1]
        endpos = len(code)
        yield (eof, '', len(line_starts), endpos - line_start + 1)
    return 0


#----------------------------------------------------------------------
# Tokenize
#----------------------------------------------------------------------
def tokenize(code, rules, eof = None):
    for info in _tokenize(code, rules, eof):
        yield Token(info[0], info[1], info[2], info[3])
    return 0


#----------------------------------------------------------------------
# validate pattern
#----------------------------------------------------------------------
def validate_pattern(pattern):
    try:
        re.compile(pattern)
    except re.error:
        return False
    return True


#----------------------------------------------------------------------
# replace '{name}' in a pattern with the text in "macros[name]"
#----------------------------------------------------------------------
def regex_expand(macros, pattern, guarded = True):
    output = []
    pos = 0
    size = len(pattern)
    while pos < size:
        ch = pattern[pos]
        if ch == '\\':
            output.append(pattern[pos:pos + 2])
            pos += 2
            continue
        elif ch != '{':
            output.append(ch)
            pos += 1
            continue
        p2 = pattern.find('}', pos)
        if p2 < 0:
            output.append(ch)
            pos += 1
            continue
        p3 = p2 + 1
        name = pattern[pos + 1:p2].strip('\r\n\t ')
        if name == '':
            output.append(pattern[pos:p3])
            pos = p3
            continue
        elif name[0].isdigit():
            output.append(pattern[pos:p3])
            pos = p3
            continue
        elif ('<' in name) or ('>' in name):
            raise ValueError('invalid pattern name "%s"'%name)
        if name not in macros:
            raise ValueError('{%s} is undefined'%name)
        if guarded:
            output.append('(?:' + macros[name] + ')')
        else:
            output.append(macros[name])
        pos = p3
    return ''.join(output)


#----------------------------------------------------------------------
# build regex info
#----------------------------------------------------------------------
def regex_build(code, macros = None, capture = True):
    defined = {}
    if macros is not None:
        for k, v in macros.items():
            defined[k] = v
    line_num = 0
    for line in code.split('\n'):
        line_num += 1
        line = line.strip('\r\n\t ')
        if (not line) or line.startswith('#'):
            continue
        pos = line.find('=')
        if pos < 0:
            raise ValueError('%d: not a valid rule'%line_num)
        head = line[:pos].strip('\r\n\t ')
        body = line[pos + 1:].strip('\r\n\t ')
        if (not head):
            raise ValueError('%d: empty rule name'%line_num)
        elif head[0].isdigit():
            raise ValueError('%d: invalid rule name "%s"'%(line_num, head))
        elif ('<' in head) or ('>' in head):
            raise ValueError('%d: invalid rule name "%s"'%(line_num, head))
        try:
            pattern = regex_expand(defined, body, guarded = not capture)
        except ValueError as e:
            raise ValueError('%d: %s'%(line_num, str(e)))
        try:
            re.compile(pattern)
        except re.error:
            raise ValueError('%d: invalid pattern "%s"'%(line_num, pattern))
        if not capture:
            defined[head] = pattern
        else:
            defined[head] = '(?P<%s>%s)'%(head, pattern)
    return defined


#----------------------------------------------------------------------
# predefined patterns
#----------------------------------------------------------------------
PATTERN_WHITESPACE = r'[ \t\r\n]+'
PATTERN_COMMENT1 = r'[#].*'
PATTERN_COMMENT2 = r'\/\/.*'
PATTERN_COMMENT3 = r'\/\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+\/'
PATTERN_MISMATCH = r'.'
PATTERN_NAME = r'\w+'
PATTERN_GNAME = r'\w(?:\w|\@)*[\']*'
PATTERN_STRING1 = r"'(?:\\.|[^'\\])*'"
PATTERN_STRING2 = r'"(?:\\.|[^"\\])*"'
PATTERN_NUMBER = r'\d+(\.\d*)?'
PATTERN_CINTEGER = r'(0x)?\d+[uUlLbB]*'
PATTERN_REPLACE = r'(?<!\\)\{\s*[a-zA-Z_]\w*\s*\}'
# PATTERN_CFLOAT = r'\d*(\.\d*)?f*'   # bad pattern, don't use
PATTERN_EPSILON = '\u03b5'
PATTERN_GMACRO = r'[%]\s*\w+'
PATTERN_OPERATOR = r'[\+\-\*\/\?\%]'


#----------------------------------------------------------------------
# predefined lexer rules
#----------------------------------------------------------------------
lex_rules = r'''
    O = [0-7]
    D = [0-9]
    NZ = [1-9]
    L = [a-zA-Z_]
    A = [a-zA-Z_0-9]
    H = [a-fA-F0-9]
    HP = (0[xX])
    E = ([Ee][+-]?{D}+)
    P = ([Pp][+-]?{D}+)
    FS = (f|F|l|L)
    IS = (((u|U)(l|L|ll|LL)?)|((l|L|ll|LL)(u|U)?))
    CP = (u|U|L)
    SP = (u8|u|U|L)

    WHITESPACE = \s+
    WS = \s+
    EOL = [\n]+
    WSEOL = {WS}|{EOL}
    COMMENT1 = [#].*
    COMMENT2 = \/\/.*
    COMMENT3 = \/\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+\/
    COMMENT = {COMMENT1}|{COMMENT2}|{COMMENT3}
    NAME = {L}{A}*
    STRING1 = '(?:\\.|[^'\\])*'
    STRING2 = "(?:\\.|[^"\\])*"
    STRING = {STRING1}|{STRING2}
    DIGIT = [0-9]
    DIGITS = {DIGIT}+
    HEX = {HP}{H}+
    DEC = {NZ}{D}*
    INTEGER = ({HEX}|{DEC})(({IS}|{CP})?)
    FLOAT = {DIGITS}((\.{DIGITS})?)({E}?)({FS}?)
    NUMBER = {INTEGER}|{FLOAT}
'''


#----------------------------------------------------------------------
# build
#----------------------------------------------------------------------
PATTERN = regex_build(lex_rules, capture = False)


#----------------------------------------------------------------------
# internal utils
#----------------------------------------------------------------------
class internal (object):

    @staticmethod
    def echo_error(text, fn = None, line_num = 0, col = None):
        name = (not fn) and '<buffer>' or fn
        if not fn:
            t = 'error: %s'%(text, )
        elif (not col) or (col < 0):
            t = 'error:%s:%d: %s'%(name, line_num, text)
        else:
            t = 'error:%s:%d:%d: %s'%(name, line_num, col, text) 
        LOG_ERROR(t)
        return 0

    @staticmethod
    def echo_warning(text, fn = None, line_num = 0, col = None):
        name = (not fn) and '<buffer>' or fn
        if not fn:
            t = 'warning: %s'%(text, )
        elif (not col) or (col < 0):
            t = 'warning:%s:%d: %s'%(name, line_num, text)
        else:
            t = 'warning:%s:%d:%d: %s'%(name, line_num, col, text) 
        LOG_WARNING(t)
        return 0

    @staticmethod
    def log_info(*args):
        LOG_INFO(*args)
        return 0

    @staticmethod
    def log_debug(*args):
        LOG_DEBUG(*args)
        return 0

    @staticmethod
    def fatal(*args):
        t = ' '.join(args)
        print('fatal: ' + t)
        print('abort')
        print()
        sys.exit(1)
        return 0

    @staticmethod
    def symbol_error(grammar, symbol, *args):
        text = ' '.join(args)
        fn, line_num = grammar.anchor_get(symbol)
        return internal.echo_error(text, fn, line_num)

    @staticmethod
    def symbol_warning(grammar, symbol, *args):
        text = ' '.join(args)
        fn, line_num = grammar.anchor_get(symbol)
        return internal.echo_warning(text, fn, line_num)

    @staticmethod
    def symbol_set_to_string(s):
        t = []
        if len(s) == 0:
            return '{ }'
        for n in s:
            t.append((str(n) == '') and '<empty>' or str(n))
        return '{ %s }'%(', '.join(t),)

    @staticmethod
    def rule_error(grammar, production, *args):
        text = ' '.join(args)
        fn, line_num = grammar.anchor_get(production)
        return internal.echo_error(text, fn, line_num)

    @staticmethod
    def rule_warning(grammar, production, *args):
        text = ' '.join(args)
        fn, line_num = grammar.anchor_get(production)
        return internal.echo_warning(text, fn, line_num)

    @staticmethod
    def bfs(initial, expand):
        open_list = collections.deque(list(initial))
        visited = set(open_list)
        while open_list:
            node = open_list.popleft()
            yield node
            for child in expand(node):
                if child not in visited:
                    open_list.append(child)
                    visited.add(child)
        return 0


#----------------------------------------------------------------------
# cstring lib
#----------------------------------------------------------------------
class cstring (object):

    @staticmethod
    def string_to_int(text, round = 0):
        text = text.strip('\r\n\t ').lstrip('+')
        minus = False
        if text.startswith('-'):
            minus = True
            text = text.lstrip('-')
        if text.startswith('0x'):
            round = 16
        elif text.startswith('0b'):
            round = 2
        text = text.rstrip('uUlLbB')
        try:
            x = int(text, round)
        except:
            x = 0
        if minus:
            x = -x
        return x

    @staticmethod
    def string_to_bool(text, defval = False):
        if text is None:
            return defval
        text = text.strip('\r\n\t ')
        if text == '':
            return defval
        if text.lower() in ('true', '1', 'yes', 't', 'enable'):
            return True
        if text.lower() in ('0', 'false', 'no', 'n', 'f', 'disable'):
            return False
        x = string_to_int(text)
        if text.isdigit() or x != 0:
            return (x != 0) and True or False
        return defval

    @staticmethod
    def string_to_float(text):
        text = text.strip('\r\n\t ').rstrip('f')
        if text.startswith('.'):
            text = '0' + text
        try:
            x = float(text)
        except:
            x = 0.0
        return x

    @staticmethod
    def string_unquote(text):
        text = text.strip("\r\n\t ")
        if len(text) < 2:
            return text.replace('"', '').replace("'", '')
        mark = text[0]
        if mark not in ('"', "'"):
            return text.replace('"', '').replace("'", '')
        if text[-1] != mark:
            return text.replace('"', '').replace("'", '')
        pos = 1
        output = []
        size = len(text)
        m = {'\\n': '\n', '\\t': '\t', '\\"': '"',
             "\\'": "\\'", '\\r': '\r', '\\\\': '\\',
             }
        while pos < size - 1:
            ch = text[pos]
            if ch == '\\':
                nc = text[pos:pos + 2]
                pos += 2
                if nc == '\\u':
                    u = text[pos:pos + 4]
                    pos += 4
                    try:
                        x = int('0x' + u, 16)
                    except:
                        x = ord('?')
                    output.append(chr(x))
                elif nc == '\\x':
                    u = text[pos:pos + 2]
                    pos += 2
                    try:
                        x = int('0x' + u, 16)
                    except:
                        x = ord('?')
                    output.append(chr(x))
                elif nc in m:
                    output.append(m[nc])
                else:
                    output.append(nc)
            else:
                output.append(ch)
                pos += 1
        return ''.join(output)

    @staticmethod
    def string_quote(text, escape_unicode = False):
        output = []
        output.append("'")
        for ch in text:
            cc = ord(ch)
            if ch == "'":
                output.append("\\'")
            elif (cc >= 256 and escape_unicode):
                nc = hex(ord(ch))[2:]
                nc = nc.rjust(4, '0')
                output.append('\\u' + nc)
            elif (cc >= 128 and escape_unicode) or cc < 32:
                nc = hex(cc)[2:]
                nc = nc.rjust(2, '0')
                output.append('\\x' + nc)
            else:
                output.append(ch)
        output.append("'")
        return ''.join(output)

    @staticmethod
    def quoted_normalize(text, double = False):
        text = text.strip('\r\n\t ')
        if len(text) == 0:
            return ''
        mark = text[0]
        if mark not in ('"', "'"):
            return None
        if len(text) < 2:
            return None
        if text[-1] != mark:
            return None
        size = len(text)
        pos = 1
        newmark = (not double) and "'" or '"'
        output = []
        output.append(newmark)
        while pos < size - 1:
            ch = text[pos]
            if mark == "'" and ch == '"':
                nc = newmark == "'" and '"' or '\\"'
                output.append(nc)
                pos += 1
            elif mark == '"' and ch == "'":
                nc = newmark == '"' and "'" or "\\'"
                output.append(nc)
                pos += 1
            elif ch == mark:
                nc = newmark == ch and ('\\' + ch) or ch
                output.append(nc)
                pos += 1
            elif ch == newmark:
                nc = '\\' + ch
                output.append(nc)
                pos += 1
            elif ch != '\\':
                output.append(ch)
                pos += 1
            else:
                nc = text[pos:pos + 2]
                pos += 2
                if newmark == '"' and nc == "\\'":
                    nc = "'"
                elif newmark == "'" and nc == '\\"':
                    nc = '"'
                elif nc == '\\':
                    nc = '\\\\'
                output.append(nc)
        output.append(newmark)
        return ''.join(output)

    @staticmethod
    def string_is_quoted(text):
        if len(text) < 2:
            return False
        mark = text[0]
        if mark not in ('"', "'"):
            return False
        if text[-1] != mark:
            return False
        return True

    @staticmethod
    def load_file_content(filename, mode = 'r'):
        if hasattr(filename, 'read'):
            try: content = filename.read()
            except: pass
            return content
        try:
            fp = open(filename, mode)
            content = fp.read()
            fp.close()
        except:
            content = None
        return content

    @staticmethod
    def load_file_text(filename, encoding = None):
        content = cstring.load_file_content(filename, 'rb')
        if content is None:
            return None
        if content[:3] == b'\xef\xbb\xbf':
            text = content[3:].decode('utf-8')
        elif encoding is not None:
            text = content.decode(encoding, 'ignore')
        else:
            text = None
            guess = [sys.getdefaultencoding(), 'utf-8']
            if sys.stdout and sys.stdout.encoding:
                guess.append(sys.stdout.encoding)
            try:
                import locale
                guess.append(locale.getpreferredencoding())
            except:
                pass
            visit = {}
            for name in guess + ['gbk', 'ascii', 'latin1']:
                if name in visit:
                    continue
                visit[name] = 1
                try:
                    text = content.decode(name)
                    break
                except:
                    pass
            if text is None:
                text = content.decode('utf-8', 'ignore')
        return text

    @staticmethod
    def tabulify (rows, style = 0):
        colsize = {}
        maxcol = 0
        output = []
        if not rows:
            return ''
        for row in rows:
            maxcol = max(len(row), maxcol)
            for col, text in enumerate(row):
                text = str(text)
                size = len(text)
                if col not in colsize:
                    colsize[col] = size
                else:
                    colsize[col] = max(size, colsize[col])
        if maxcol <= 0:
            return ''
        def gettext(row, col):
            csize = colsize[col]
            if row >= len(rows):
                return ' ' * (csize + 2)
            row = rows[row]
            if col >= len(row):
                return ' ' * (csize + 2)
            text = str(row[col])
            padding = 2 + csize - len(text)
            pad1 = 1
            pad2 = padding - pad1
            return (' ' * pad1) + text + (' ' * pad2)
        if style == 0:
            for y, row in enumerate(rows):
                line = ''.join([ gettext(y, x) for x in range(maxcol) ])
                output.append(line)
        elif style == 1:
            if rows:
                newrows = rows[:1]
                head = [ '-' * colsize[i] for i in range(maxcol) ]
                newrows.append(head)
                newrows.extend(rows[1:])
                rows = newrows
            for y, row in enumerate(rows):
                line = ''.join([ gettext(y, x) for x in range(maxcol) ])
                output.append(line)
        elif style == 2:
            sep = '+'.join([ '-' * (colsize[x] + 2) for x in range(maxcol) ])
            sep = '+' + sep + '+'
            for y, row in enumerate(rows):
                output.append(sep)
                line = '|'.join([ gettext(y, x) for x in range(maxcol) ])
                output.append('|' + line + '|')
            output.append(sep)
        return '\n'.join(output)

    # match string and return matched text and remain text
    @staticmethod
    def string_match(source, pattern, group = 0):
        m = re.match(pattern, source)
        if m:
            matched = m.group(group)
            span = m.span()
            return matched, source[span[1]:]
        return None, source


#----------------------------------------------------------------------
# lex analyze
#----------------------------------------------------------------------
class GrammarLex (object):

    def __init__ (self):
        self.specific = self._build_pattern()

    def _build_pattern (self):
        spec = [
                    (None, PATTERN_COMMENT1),       # ignore
                    (None, PATTERN_COMMENT2),       # ignore
                    (None, PATTERN_COMMENT3),       # ignore
                    (None, PATTERN_WHITESPACE),     # ignore
                    (self._handle_string, PATTERN_STRING1),
                    (self._handle_string, PATTERN_STRING2),
                    (self._handle_macro, PATTERN_GMACRO),
                    (self._handle_integer, PATTERN_CINTEGER),
                    (self._handle_float, PATTERN_NUMBER),
                    ('BAR', r'\|'),
                    ('END', r'[;]'),
                    (':', r'[:]'),
                    ('LEX', r'[@].*'),
                    ('NAME', PATTERN_GNAME),
                    ('NAME', PATTERN_NAME),
                    (self._handle_action, r'\{[^\{\}]*\}'),
                    (None, r'\%\%'),
                    ('OPERATOR', r'[\+\-\*\/\?\%]'),
                    ('MISMATCH', r'.'),
                ]
        return spec

    def _handle_string (self, value):
        text = cstring.quoted_normalize(value)
        return ('STRING', text)

    def _handle_integer (self, value):
        return ('NUMBER', cstring.string_to_int(value))

    def _handle_float (self, value):
        if '.' not in value:
            return self._handle_integer(value)
        return ('NUMBER', cstring.string_to_float(value))

    def _handle_macro (self, value):
        value = value.strip('\r\n\t ').replace(' ', '')
        return ('MACRO', value)

    def _handle_action (self, value):
        value = value.strip('\r\n\t ')
        return ('ACTION', value)

    def process (self, source):
        tokens = {}
        for token in tokenize(source, self.specific):
            # print(repr(token))
            line_num = token.line
            if line_num not in tokens:
                tokens[line_num] = []
            tokens[line_num].append(token)
            # print(token)
        return tokens


#----------------------------------------------------------------------
# load grammar file
#----------------------------------------------------------------------
class GrammarLoader (object):

    def __init__ (self):
        self.line_num = 0
        self.file_name = ''
        self.code = 0
        self.source = ''
        self.precedence = 0
        self.srcinfo = {}
        self.lex = GrammarLex()

    def error (self, *args):
        text = ' '.join(args)
        fn = (not self.file_name) and '<buffer>' or self.file_name
        internal.echo_error(text, fn, self.line_num)
        return 0

    def error_token (self, token, text = None):
        fn = (not self.file_name) and '<buffer>' or self.file_name
        if text is None:
            text = 'unexpected token: %r'%(token.value, )
        internal.echo_error(text, fn, token.line, token.column)
        return 0

    def load (self, source, file_name = ''):
        if isinstance(source, str):
            self.source = source
        else:
            self.source = source.read()
            if isinstance(self.code, bytes):
                self.code = self.code.decode('utf-8', 'ignore')
        self.file_name = file_name and file_name or '<buffer>'
        hr = self._scan_grammar()
        if hr != 0:
            return None
        return self.g

    def load_from_file (self, file_name, encoding = None):
        self.source = cstring.load_file_text(file_name, encoding)
        self.file_name = file_name
        hr = self._scan_grammar()
        if hr != 0:
            return None
        return self.g

    def _scan_grammar (self):
        self.g = Grammar()
        self.g.start = None
        self.current_symbol = None
        self.line_num = 0
        self.precedence = 0
        self._cache = []
        self.srcinfo.clear()
        tokens = self.lex.process(self.source)
        keys = list(tokens.keys())
        keys.sort()
        for line_num in keys:
            self.line_num = line_num
            args = tokens[line_num]
            hr = 0
            if not args:
                continue
            if args[0].name == 'MACRO':
                hr = self._process_macro(args)
            elif args[0].name == 'LEX':
                hr = self._process_lexer(args)
            else:
                hr = self._process_grammar(args)
            if hr != 0:
                return hr
        if len(self._cache) > 0:
            self._process_rule(self._cache)
        self.g.update()
        if self.g.start is None:
            if len(self.g.production) > 0:
                self.g.start = self.g.production[0].head
        if self.g.start:
            symbol = self.g.start.__copy__()
            symbol.term = (symbol.name in self.g.terminal)
            self.g.start = symbol
        for n in self.srcinfo:
            if not self.g.anchor_has(n):
                t = self.srcinfo[n]
                self.g.anchor_set(n, t[0], t[1])
        self.g.file_name = self.file_name
        return 0

    def _process_grammar (self, args):
        for arg in args:
            self._cache.append(arg)
            if arg.name == 'END':
                hr = self._process_rule(self._cache)
                self._cache.clear()
                if hr != 0:
                    return hr
        return 0

    def _process_rule (self, args):
        if not args:
            return 0
        argv = [n for n in args]
        if argv[0].name == 'STRING':
            self.error_token(argv[0], 'string literal %s can not have a rule'%argv[0].value)
            return 1
        elif argv[0].name != 'NAME':
            self.error_token(argv[0], 'wrong production head: "%s"'%argv[0].value)
            return 1
        elif argv[-1].name != 'END':
            self.error_token(argv[-1], 'missing ";"')
            return 2
        head = load_symbol(argv[0].value)
        argv = argv[:-1]
        if len(argv) < 2:
            self.error_token(argv[0], 'require ":" after "%s"'%(argv[0].value))
            return 3
        elif argv[1].name != ':':
            self.error_token(argv[1], 'require ":" before "%s"'%(argv[1].value))
            return 4
        cache = []
        for arg in argv[2:]:
            if arg.name == 'BAR':
                hr = self._add_rule(head, cache)
                cache.clear()
                if hr != 0:
                    return hr
            else:
                cache.append(arg)
        hr = self._add_rule(head, cache)
        if hr != 0:
            return hr
        if not self.g.anchor_has(head):
            self.g.anchor_set(head, self.file_name, argv[0].line)
        return 0

    def _add_rule (self, head, argv):
        body = []
        # print('add', head, ':', argv)
        pos = 0
        size = len(argv)
        action = {}
        precedence = None
        while pos < size:
            token = argv[pos]
            if token.name == 'STRING':
                text = token.value
                value = cstring.string_unquote(text)
                if not value:
                    pos += 1
                    continue
                elif len(text) < 2:
                    self.error_token(token, 'bad string format %s'%text)
                    return 10
                elif len(text) == 2:
                    pos += 1
                    continue
                symbol = load_symbol(token.value)
                body.append(symbol)
                pos += 1
                self.g.push_token(symbol)
            elif token.name == 'NAME':
                symbol = load_symbol(token.value)
                body.append(symbol)
                pos += 1
            elif token.name == 'OPERATOR':
                text = repr(token.value)
                symbol = load_symbol(text)
                body.append(symbol)
                pos += 1
                self.g.push_token(symbol)
            elif token.name == 'MACRO':
                cmd = token.value.strip()
                pos += 1
                if cmd == '%prec':
                    token = argv[pos]
                    prec = token.value
                    pos += 1
                    if prec not in self.g.precedence:
                        self.error_token(token, 'undefined precedence %s'%prec)
                        return 11
                    precedence = self.g.precedence[prec]
                elif cmd in ('%empty', '%e', '%epsilon'):
                    pos += 1
                    continue
            elif token.name == 'ACTION':
                i = len(body)
                if i not in action:
                    action[i] = []
                act = (token.value, i)
                action[i].append(act)
                pos += 1
            elif token.name == 'NUMBER':
                self.error_token(token)
                return 11
            elif token.name == 'MISMATCH':
                self.error_token(token)
                return 12
            else:
                self.error_token(token)
                return 13
            pass
        p = Production(head, body)
        p.precedence = precedence
        if len(action) > 0:
            p.action = action
        # print('action:', action)
        self.g.append(p)
        for token in argv:
            if token.value not in self.srcinfo:
                t = (self.file_name, token.line)
                self.srcinfo[token.value] = t
        if argv:
            self.g.anchor_set(p, self.file_name, argv[0].line)
        return 0

    def _process_macro (self, args):
        macro = args[0]
        argv = args[1:]
        cmd = macro.value
        if cmd == '%token':
            for n in argv:
                if n.name != 'NAME':
                    self.error_token(n)
                    return 1
                self.g.push_token(n.value)
        elif cmd in ('%left', '%right', '%nonassoc'):
            assoc = cmd[1:].strip()
            for n in argv:
                if n.name not in ('NAME', 'STRING'):
                    # print('fuck', n)
                    self.error_token(n)
                    return 1
                self.g.push_precedence(n.value, self.precedence, assoc)
            self.precedence += 1
        elif cmd == '%start':
            if len(argv) == 0:
                self.error_token(macro, 'expect start symbol')
                return 2
            token = argv[0]
            if token.name in ('STRING',):
                self.error_token(token, 'can not start from a terminal')
                return 3
            elif token.name != 'NAME':
                self.error_token(token, 'must start from a non-terminal symbol')
                return 4
            symbol = grammar.load_symbol(argv[0].value)
            if symbol.name in self.g.terminal:
                symbol.term = True
            if symbol.term:
                self.error_token(token, 'could not start from a terminal')
                return 5
            self.g.start = symbol
        return 0

    def _process_lexer (self, args):
        assert len(args) == 1
        args[0].column = -1
        origin: str = args[0].value.strip('\r\n\t ')
        m = re.match(r'[@]\s*(\w+)', origin)
        if m is None:
            self.error_token(args[0], 'bad lex declaration')
            return 1
        head: str = ('@' + m.group(1)).strip('\r\n\t ')
        body: str = origin[m.span()[1]:].strip('\r\n\t ')
        if head in ('@ignore', '@skip'):
            if not ctr.validate_pattern(body):
                self.error_token(args[0], 'bad regex pattern: ' + repr(body))
                return 2
            self.g.push_scanner(('ignore', body))
        elif head == '@match':
            m = re.match(r'(\{[^\{\}]*\}|\w+)\s+(.*)', body)
            if m is None:
                self.error_token(args[0], 'bad lex matcher definition')
                return 3
            name = m.group(1).strip('\r\n\t ')
            pattern = m.group(2).strip('\r\n\t ')
            if not validate_pattern(pattern):
                self.error_token(args[0], 'bad regex pattern: ' + repr(pattern))
                return 4
            # print('matched name=%r patterm=%r'%(name, pattern))
            self.g.push_scanner(('match', name, pattern))
            if not name.startswith('{'):
                self.g.push_token(name)
        elif head == '@import':
            part = re.split(r'\W+', body)
            part = list(filter(lambda n: (n.strip('\r\n\t ') != ''), part))
            if len(part) == 1:
                name = part[0].strip()
                if not name:
                    self.error_token(args[0], 'expecting import name')
                    return 5
                if name not in PATTERN:
                    self.error_token(args[0], 'invalid import name "%s"'%name)
                    return 6
                self.g.push_scanner(('import', name, name))
                if not name.startswith('{'):
                    self.g.push_token(name)
            elif len(part) == 3:
                name = part[0].strip()
                if not name:
                    self.error_token(args[0], 'expecting import name')
                    return 7
                asname = part[2].strip()
                if not asname:
                    self.error_token(args[0], 'expecting aliasing name')
                    return 8
                if part[1].strip() != 'as':
                    self.error_token(args[0], 'invalid import statement')
                    return 9
                if name not in PATTERN:
                    self.error_token(args[0], 'invalid import name "%s"'%name)
                    return 10
                self.g.push_scanner(('import', asname, name))
                if not asname.startswith('{'):
                    self.g.push_token(asname)
        else:
            self.error_token(args[0], 'bad lex command: %r'%head)
        return 0


#----------------------------------------------------------------------
# load from file
#----------------------------------------------------------------------
def load_from_file(filename) -> Grammar:
    loader = GrammarLoader()
    g = loader.load_from_file(filename)
    if not g:
        sys.exit(1)
    return g


#----------------------------------------------------------------------
# load from string
#----------------------------------------------------------------------
def load_from_string(code) -> Grammar:
    loader = GrammarLoader()
    g = loader.load(code)
    if not g:
        sys.exit(1)
    return g



#----------------------------------------------------------------------
# testing suit
#----------------------------------------------------------------------
if __name__ == '__main__':
    def test1():
        g = load_from_file('grammar/test_bnf.txt')
        g.print()
        return 0
    test1()


