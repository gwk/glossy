# Dedicated to the public domain under CC0: https://creativecommons.org/publicdomain/zero/1.0/.

import re

from argparse import Namespace
from pprint import pformat
from typing import *
from pithy.fs import add_file_execute_permissions
from pithy.io import *
from pithy.string_utils import render_template
from .defs import ModeTransitions
from .rules import Rule


def output_python3(path: str, patterns: Dict[str, Rule], mode_rule_names: Dict[str, List[str]], transitions: ModeTransitions,
  rule_descs: Dict[str, str], license: str, args: Namespace):

  py_patterns: List[str] = []
  for name, rule in patterns.items():
    py_pattern = rule.genRegex(flavor='py')
    py_patterns.append(f"\n    {name}=r'{py_pattern}',")

  py_modes: List[str] = []
  for mode, rule_names in sorted(mode_rule_names.items()):
    names_str = ''.join(f'\n      {n!r},' for n in rule_names)
    py_modes.append(f'\n    {mode}={{{names_str}}}')

  py_transitions: List[str] = [f'\n    ({a}, {b}) : ({c}, {d})' for (a, b), (c, d) in transitions.items()]

  with open(path, 'w', encoding='utf8') as f:
    src = render_template(template,
      license=license,
      rules_path=args.path,
      patterns=''.join(py_patterns),
      modes=''.join(py_modes),
      transitions=''.join(py_transitions),
      Name=args.type_prefix,
      rule_descs=pformat(rule_descs, indent=2),
    )
    f.write(src)
    if args.test:
      test_src = render_template(test_template, Name=args.type_prefix)
      f.write(test_src)


template = r'''# ${license}
# This file was generated by legs from ${rules_path}.

from pithy.lex import Lexer as _Lexer
from typing import Match, Optional


${Name}Token = Match[str]


class ${Name}Source:

  def __init__(self, name: str, text: str) -> None:
    self.name = name
    self.text = text
    self.newline_positions: List[int] = []

  def __repr__(self): return f'{self.__class__.__name__}({self.name})'

  def lex(self) -> '${Name}Lexer':
    return ${Name}Lexer(source=self)

  def get_line_index(self, pos: int) -> int:
    for (index, newline_pos) in enumerate(self.newline_positions):
      if pos <= newline_pos:
        return index
    return len(self.newline_positions)

  def get_line_start(self, pos: int) -> int:
    return self.text.rfind('\n', 0, pos) + 1 # rfind returns -1 for no match, happens to work perfectly.

  def get_line_end(self, pos: int) -> int:
    line_end = self.text.find('\n', pos)
    return len(self.text) if line_end == -1 else line_end

  def diagnostic_for_token(self, token: ${Name}Token, msg: str = '', show_missing_newline: bool = True) -> str:
    pos = token.start()
    end = token.end()
    line_pos = self.get_line_start(pos)
    line_idx = self.text.count('\n', 0, pos) # number of newlines preceeding pos.
    return self.diagnostic_for_pos(pos=pos, end=end, line_pos=line_pos, line_idx=line_idx, msg=msg, show_missing_newline=show_missing_newline)

  def diagnostic_at_end(self, msg: str = '', show_missing_newline: bool = true) -> str:
    last_pos = len(self.text) - 1
    line_pos: Int
    line_idx: Int
    newline_pos = self.text.rfind('\n')
    if newline_pos >= 0: #
      if newline_pos == last_pos: # terminating newline.
        line_pos = self.get_line_start(pos: newline_pos)
        line_idx = self.text.count('\n', 0, newline_pos) # number of newlines preceeding newline_pos.
      else: # no terminating newline.
        line_pos = newline_pos + 1
        line_idx = len(newline_positions)
    else:
      line_pos = 0
      line_idx = 0
    return self.diagnostic(pos=last_pos, line_pos=line_pos, line_idx=line_idx, msg=msg)

  def diagnostic_for_pos(self, pos: int, end: int = None, line_pos: int, line_idx: int, msg: str = '', show_missing_newline: bool = True) -> str:

    if end is None: end = pos
    line_end = self.get_line_end(pos)
    if end <= line_end: # single line.
      return self._diagnostic(pos=pos, end=end, line_pos=line_pos, line_idx=line_idx, line_str=self.text[line_pos:line_end],
        msg=msg, show_missing_newline=show_missing_newline)
    else: # multiline.
      end_line_idx = self.get_line_index(pos)
      end_line_pos = self.get_line_start(end)
      end_line_end = self.get_line_end(end)
      return (
        self._diagnostic(pos=pos, end=line_end, line_pos=line_pos, line_idx=line_idx, line_str=self.text[line_pos:line_end],
          msg=msg, show_missing_newline=show_missing_newline) +
        self._diagnostic(pos=end_line_pos, end=end, line_pos=end_line_pos, line_idx=end_line_idx, line_str=self.text[end_line_pos:end_line_end],
          msg=msg, show_missing_newline=show_missing_newline))

  def _diagnostic(self, pos: int, end: int, line_pos: int, line_idx: int, line_str: str, msg: str, show_missing_newline: bool) -> str:

    assert pos >= 0
    assert pos <= end
    assert line_pos <= pos
    assert end <= line_pos + len(line_str)

    tab = '\t'
    newline = '\n'
    space = ' '
    caret = '^'
    tilde = '~'

    line_end = line_pos + len(line_str)

    #def decode(bytes_: bytes) -> str: pass

    src_line: str
    if line_str[-1] == newline:
      last_idx = len(line_str) - 1
      s = line_str[:-1]
      if pos == last_idx or end == line_end:
        src_line = s + "\u23CE" # RETURN SYMBOL.
      else:
        src_line = s
    elif show_missing_newline:
      src_line = line_str + "\u23CE\u0353" # RETURN SYMBOL, COMBINING X BELOW.
    else:
      src_line = line_str

    src_bar = "| " if src_line else "|"

    under_chars = []
    for char in line_str[:(pos - line_pos)]:
      under_chars.append(tab if char == tab else space)
    if pos >= end:
      under_chars.append(caret)
    else:
      for _ in range(pos, end):
        under_chars.append(tilde)
    underline = ''.join(under_chars)

    def col_str(pos: int) -> str:
      return (pos - line_pos) + 1

    col = f'{col_str(pos)}-{col_str(end)}' if pos < end else col_str(pos)

    msg_space = "" if (not msg or msg.startswith('\n')) else " "
    return f'{self.name}:{line_idx+1}:{col}:{msg_space}{msg}\n{src_bar}{src_line}\n  {underline}\n'


class ${Name}Lexer:

  def __init__(self, source: ${Name}Source) -> None:
    self.source = source

  def __iter__(self):
    return iter(_lexer.lex(self.source.text))


_lexer = _Lexer(
  invalid='invalid',
  patterns=dict(${patterns}),
  modes=dict(${modes}),
  transitions={${transitions}})

rule_descs = ${rule_descs}
'''


test_template = r'''

# Legs test main.

def test(index: int, arg: str) -> None:
  name = f'arg{index}'
  print(f'\n{name}: {ployRepr(arg)}')
  source = ${Name}Source(name=name, text=arg)
  for token in source.lex():
    print(source.diagnostic_for_token(token, msg=rule_descs[token.lastgroup], show_missing_newline=False),
      end='')

def ployRepr(string: str) -> str:
  r = ["'"]
  for char in string:
    if char == '\\': r.append('\\\\')
    elif char == "'": r.append("\\'")
    elif 0x20 <= ord(char) <= 0x7E: r.append(char)
    elif char == '\0': r.append('\\0')
    elif char == '\t': r.append('\\t')
    elif char == '\n': r.append('\\n')
    elif char == '\r': r.append('\\r')
    else: r.append(f'\\{hex(ord(char))};')
  r.append("'")
  return ''.join(r)

def main() -> None:
  from sys import argv
  for i, arg in enumerate(argv):
    if i == 0: continue
    test(index=i, arg=arg)

if __name__ == '__main__': main()
'''
