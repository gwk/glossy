# Dedicated to the public domain under CC0: https://creativecommons.org/publicdomain/zero/1.0/.

'''
Simple lexing using python regular expressions.
'''

import re
from typing import Any, Container, Dict, FrozenSet, Iterable, Iterator, List, Match, NoReturn, Optional, Pattern, Tuple, cast


class LexError(Exception): pass

Token = Match[str]


class Lexer:
  '''
  Note: A zero-length match, e.g. r'^' causes an exception; otherwise the stream would never advance.
  '''
  # One way to support zero-length tokens, e.g. r'^\s*' for Python indent tokens,
  # would be to swap out the main regex for one with the pattern in question omitted,
  # for the next iteration only.

  class DefinitionError(Exception): pass

  def __init__(self, *, flags='', invalid=None, patterns:Dict[str,str], modes:Dict[str,Iterable[str]]={},
   transitions:Dict[Tuple[str,str],Tuple[str,Iterable[str]]]={}) -> None:
    self.invalid = invalid

    # validate flags.
    for flag in flags:
      if flag not in 'aiLmsux':
        raise Lexer.DefinitionError(f'invalid global regex flag: {flag}')
    flags_pattern = f'(?{flags})' if flags else ''
    is_extended = 'x' in flags

    # validate patterns.
    if not patterns: raise Lexer.DefinitionError('Lexer instance must define at least one pattern')
    self.patterns: Dict[str,str] = {}
    for n, v in patterns.items():
      validate_name(n)
      if n == invalid:
        raise Lexer.DefinitionError(f'{n!r} pattern name collides with the invalid token name')
      if not isinstance(v, str): # TODO: also support bytes.
        raise Lexer.DefinitionError(f'{n!r} pattern value must be a string; found {v!r}')
      pattern = f'{flags_pattern}(?P<{n}>{v})'
      try: r = re.compile(pattern) # compile each expression by itself to improve error clarity.
      except Exception as e:
        lines = [f'{n!r} pattern is invalid: {pattern}']
        if flags: lines.append(f'global flags: {flags!r}')
        if is_extended and re.search('(?<!\\)#)', v): lines.append('unescaped verbose mode comments break lexer')
        msg = '\n  note: '.join(lines)
        raise Lexer.DefinitionError(msg) from e
      for group_name in r.groupindex:
        if group_name in patterns and group_name != n:
          raise Lexer.DefinitionError(f'{n!r} pattern contains a conflicting capture group name: {group_name!r}')
      self.patterns[n] = pattern

    # validate modes.
    self.modes: Dict[str,FrozenSet[str]] = {}
    main = None
    if modes:
      for mode, names in modes.items():
        if not main: main = mode
        if mode in patterns:
          raise Lexer.DefinitionError(f'mode name conflicts with pattern name: {mode!r}')
        expanded = set()
        if isinstance(names, str):
          raise Lexer.DefinitionError(f'mode {mode!r} value should be a iterable of names, not a str: {names!r}')
        for name in names:
          if re.fullmatch(r'\w+', name):
            if name in patterns: expanded.add(name)
            else: raise Lexer.DefinitionError(f'mode {mode!r} includes nonexistant pattern: {name!r}')
          else:
            try:
              matching = {p for p in self.patterns if re.fullmatch(name, p)}
            except Exception:
              raise Lexer.DefinitionError(f'mode {mode!r} includes invalid wildcard pattern regex: {name}')
            if not matching:
              raise Lexer.DefinitionError(f'mode {mode!r} wildcard pattern regex does not match any patterns: {name}')
            expanded.update(matching)
        self.modes[mode] = frozenset(expanded)
    else:
      self.modes = { 'main' : frozenset(self.patterns) }
      main = 'main'

    # validate transitions.
    assert main is not None
    self.main: str = main
    self.transitions:Dict[Tuple[str,str],Tuple[str,FrozenSet[str]]] = {}
    for (parent_mode, enter), (child_mode, leaves) in transitions.items():
      if parent_mode not in modes: raise Lexer.DefinitionError(f'unknown parent mode: {parent_mode!r}')
      if child_mode not in modes: raise Lexer.DefinitionError(f'unknown child mode: {child_mode!r}')
      if enter not in patterns: raise Lexer.DefinitionError(f'unknown mode enter pattern: {enter!r}')
      if isinstance(leaves, str):
        leaves = [leaves]
      for leave in leaves:
        if leave not in patterns: raise Lexer.DefinitionError(f'unknown mode leave pattern: {leave!r}')
      self.transitions[(parent_mode, enter)] = (child_mode, frozenset(leaves))

    choice_sep = '\n| ' if 'x' in flags else '|'
    def compile_mode(mode: str, pattern_names: FrozenSet[str]) -> Pattern:
      return re.compile(choice_sep.join(pattern for name, pattern in self.patterns.items() if name in pattern_names))
      #^ note: iterate over self.patterns.items (not pattern_names) because the dict preserves the original pattern order.

    self.regexes = { mode : compile_mode(mode, pattern_names) for mode, pattern_names in self.modes.items() }

    self.inv_re = re.compile(f'(?s)(?P<{self.invalid}>.+)' if self.invalid else '(?s).+')


  def _lex_mode(self, regex:Pattern, string:str, pos:int, end:int) -> Iterator[Token]:
    def lex_inv(end:int) -> Token:
      inv_match = self.inv_re.match(string, pos, end) # create a real match object.
      assert inv_match is not None
      if self.invalid: return inv_match
      raise LexError(inv_match)
    while pos < end:
      token = regex.search(string, pos)
      if not token:
        yield lex_inv(end)
        break
      s, e = token.span()
      if pos < s:
        yield lex_inv(s)
      if s == e:
        raise Lexer.DefinitionError('Zero-length patterns are disallowed.\n'
          f'  kind: {token.lastgroup}; token: {token}')
      yield token
      pos = e

  def _lex_gen(self, stack:List[Tuple[str,FrozenSet[str]]], string:str, p:int, e:int, drop:Container[str],
   eot:bool) -> Iterator[Token]:
    while p < e:
      mode, exit_names = stack[-1]
      regex = self.regexes[mode]
      for token in self._lex_mode(regex, string, pos=p, end=e):
        p = token.end()
        if not drop or token.lastgroup not in drop:
          yield token
        if token.lastgroup in exit_names:
          stack.pop()
          break
        try: frame = self.transitions[(mode, token.lastgroup)]
        except KeyError: pass
        else:
          stack.append(frame)
          break
    if eot:
      yield eot_token(string[:e])


  def lex(self, string:str, pos:int=0, end:Optional[int]=None, drop:Container[str]=(), eot=False) -> Iterator[Token]:
    if pos < 0:
      pos = len(string) + pos
    if end is None:
      end = len(string)
    elif end < 0:
      end = len(string) + end
    _e: int = end # typing hack.
    return self._lex_gen(stack=[(self.main, frozenset())], string=string, p=pos, e=_e, drop=drop, eot=eot)


  def lex_stream(self, stream:Iterable[str], drop:Container[str]=(), eot=False) -> Iterator[Token]:
    '''
    Note: the yielded Token objects have positions relative to input string that each was lexed from.'
    '''
    stack:List[Tuple[str,FrozenSet[str]]] = [(self.main, frozenset())]
    string = ''
    for string in stream:
      if string:
        yield from self._lex_gen(stack=stack, string=string, p=0, e=len(string), drop=drop, eot=False)
    if eot:
      yield eot_token(string)


_eot_re = re.compile(r'(?P<end_of_text>$)')

def eot_token(string:str) -> Token:
  'Create a token representing the end-of-text.'
  return cast(Token, _eot_re.search(string, len(string)))

_pos_re = re.compile(r'')
def pos_token(token:Token) -> Token:
  'Create a new token with the same position as `token` but with zero length.'
  return cast(Token, _pos_re.match(token.string, token.start()))


def token_fail(path:str, token:Token, msg:str) -> NoReturn:
  'Print a formatted parsing failure to std err and exit.'
  exit(token_diagnostic(token, prefix=path, msg=msg))


def token_diagnostic(token:Token, prefix:str, msg:str, pos:Optional[int]=None, end:Optional[int]=None) -> str:
  'Return a formatted parser error message.'
  string = token.string
  p, e = token.span()
  if pos is None: pos = p
  else: assert pos >= p
  if end is None: end = e
  else: assert end <= e
  line_num = string.count('\n', 0, pos) # number of newlines preceeding pos.
  line_start = string.rfind('\n', 0, pos) + 1 # rfind returns -1 for no match, happens to work perfectly.
  line_end = string.find('\n', pos)
  if line_end == -1: line_end = len(string)
  line = string[line_start:line_end]
  col = pos - line_start
  indent = ''.join('\t' if c == '\t' else ' ' for c in line[:col])
  src_bar = '| ' if line else '|'
  underline = '~' * (min(end - pos, len(line))) or '^'
  return f'{prefix}:{line_num+1}:{col+1}: {msg}\n{src_bar}{line}\n  {indent}{underline}'


def token_line_col_0(token:Token) -> Tuple[int,int]:
  'Return a pair of 0-indexed line and column numbers for a token.'
  string = token.string
  pos = token.start()
  line_num = string.count('\n', 0, pos) # number of newlines preceeding pos.
  line_start = string.rfind('\n', 0, pos) + 1 # rfind returns -1 for no match, happens to work perfectly.
  return (line_num, pos - line_start)


def validate_name(name:str) -> str:
  if not valid_name_re.fullmatch(name):
    raise Lexer.DefinitionError(f'invalid name: {name!r}')
  if name in reserved_names:
    raise Lexer.DefinitionError(f'name is reserved: {name!r}')
  return name

valid_name_re = re.compile(r'[A-Za-z_]\w*')

reserved_names = frozenset({'end_of_text'})
