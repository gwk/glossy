#!/usr/bin/env python3
# Dedicated to the public domain under CC0: https://creativecommons.org/publicdomain/zero/1.0/.

import os
import re
import sys
from argparse import ArgumentParser
from cProfile import Profile
from pstats import Stats
from os.path import dirname
from typing import Any, Dict, Iterable, List, Optional, Set, TextIO, Tuple, Union
from pithy.io import errL, errSL
from pithy.path import path_rel_to_current_or_abs
from sys import prefix as sys_prefix


def main() -> None:
  sort_keys_l = ', '.join(sort_keys)
  sort_keys_desc = f'sort keys: {sort_keys_l}.'
  parser = ArgumentParser(description='Run a python script under the Python cProfile profiler.')
  parser.add_argument('-sort', nargs='+', default=['cumulative', 'filename', 'name'], help=sort_keys_desc)
  parser.add_argument('-filter', nargs='+', default=[], help='filtering clauses.')
  parser.add_argument('cmd', nargs='+', help='the command to run.')
  args = parser.parse_args()

  cmd = args.cmd
  cmd_path = cmd[0]

  def filter_clause(word:Any) -> Any:
    for T in (int, float):
      try: return T(word)
      except ValueError: pass
    return word

  filter_clauses = [filter_clause(word) for word in args.filter]

  with open(cmd_path, 'rb') as f:
    code = compile(f.read(), cmd_path, 'exec')

  globals_ = {
    '__file__': cmd_path,
    '__name__': '__main__',
    '__package__': None,
    '__cached__': None,
  }

  sys.argv[:] = cmd
  # also need to fix the search path to imitate the regular interpreter.
  sys.path[0] = dirname(cmd_path) # not sure if this is right in all cases.

  profile = Profile()
  exit_code = 0
  try:
    profile.runctx(code, globals=globals_, locals={})
  except SystemExit as e:
    exit_code = e.code
  except BaseException:
    from traceback import TracebackException
    exit_code = 1 # exit code that Python returns when an exception raises to toplevel.
    # Format the traceback as it would appear when run standalone.
    traceback = TracebackException(*sys.exc_info()) # type: ignore
    # note: the traceback will contain stack frames from the host.
    # this can be avoided with a fixup function, but does not seem necessary at this point. See coven.py for an example.
    #fixup_traceback(traceback)
    print(*traceback.format(), sep='', end='', file=sys.stderr)

  print('\n', '=' * 64, sep='')

  stats = CustomStats(profile)

  if stats.fcn_list:
    print(f'Ordered by: {stats.sort_type}.\n')
  else:
    print('Random listing order was used.\n')

  stats.sort_stats(*args.sort)
  stats.display_stats(*filter_clauses)
  #print('\nCallers:')
  #stats.display_callers(*filter_clauses)
  #print('\nCallees:')
  #stats.display_callees(*filter_clauses)


sort_keys = {
  'calls'       : 'call count',
  'cumtime'     : 'cumulative time',
  'cumulative'  : 'cumulative time',
  'file'        : 'file name',
  'filename'    : 'file name',
  'line'        : 'line number',
  'module'      : 'file name',
  'name'        : 'function name',
  'ncalls'      : 'call count',
  'nfl'         : 'name/file/line',
  'pcalls'      : 'primitive call count',
  'stdname'     : 'standard name',
  'time'        : 'internal time',
  'tottime'     : 'internal time',
}


Func = Tuple[str,int,str] #
Selector = Union[str,float,int]

class CustomStats(Stats):

  all_callees:Optional[Dict]
  files:List[TextIO]
  max_name_len:int
  fcn_list:List[Func]
  prim_calls:int
  sort_type:str
  stats:Dict[Func,Any]
  stream:TextIO
  top_level:Set[Func]
  total_calls:int
  total_tt:float


  def print(self, *items:Any, sep=' ', end='\n') -> None:
    print(*items, file=self.stream, sep=sep, end=end)


  def display_stats(self, *amount:Selector) -> None:
    if self.files:
      for filename in self.files:
        self.print(filename)
      self.print()

    for func in self.top_level:
      self.print(get_func_name(func))

    self.print(f'{self.total_calls} function calls ({self.prim_calls} primitive calls) in {self.total_tt:.3f} seconds')
    self.print()
    width, stat_list = self.get_display_list(amount)
    if stat_list:
      self.print_title()
      for func in stat_list:
        self.display_line(func)
      self.print()
      self.print()


  def display_callees(self, *amount:Selector) -> None:
    width, stat_list = self.get_display_list(amount)
    if not stat_list: return
    self.calc_callees()
    assert self.all_callees is not None
    self.print_call_heading(width, "CALLEE")
    for func in stat_list:
      if func in self.all_callees:
          self.display_call_line(width, func, self.all_callees[func])
      else:
          self.display_call_line(width, func, {})
    print(file=self.stream)
    print(file=self.stream)


  def display_callers(self, *amount:Selector) -> None:
    width, stat_list = self.get_display_list(amount)
    if not stat_list: return
    self.print_call_heading(width, "CALLER")
    for func in stat_list:
      cc, nc, tt, ct, callers = self.stats[func]
      self.display_call_line(width, func, callers, "<-")
    print(file=self.stream)
    print(file=self.stream)


  def eval_display_amount(self, sel:Selector, stat_list:List[Func], msg:str) -> Tuple[List[Func], str]:
    new_list = stat_list
    if isinstance(sel, str):
      try:
        rex = re.compile(sel)
      except re.error:
        msg += "   <Invalid regular expression %r>\n" % sel
        return new_list, msg
      new_list = []
      for func in stat_list:
        if rex.search(fmt_func(func)):
            new_list.append(func)
    else:
      count = len(stat_list)
      if isinstance(sel, float) and 0.0 <= sel < 1.0:
        count = int(count * sel + .5)
        new_list = stat_list[:count]
      elif isinstance(sel, int) and 0 <= sel < count:
        count = sel
        new_list = stat_list[:count]
    if len(stat_list) != len(new_list):
      msg += "   List reduced from %r to %r due to restriction <%r>\n" % (
        len(stat_list), len(new_list), sel)
    return new_list, msg


  def get_display_list(self, sel_list:Iterable[Selector]) -> Tuple[int, List[Func]]:
    stat_list = list(self.fcn_list[:]) if self.fcn_list else list(self.stats.keys())

    width = self.max_name_len

    for selection in sel_list:
      stat_list, msg = self.eval_display_amount(selection, stat_list, msg)

    count = len(stat_list)

    if not stat_list:
      return 0, stat_list
    if count < len(self.stats):
      width = 0
      for func in stat_list:
        if  len(fmt_func(func)) > width:
            width = len(fmt_func(func))
    return width+2, stat_list


  def print_call_heading(self, name_size:int, column_title:str) -> None:
    print("Function ".ljust(name_size) + column_title, file=self.stream)
    # print sub-header only if we have new-style callers
    subheader = False
    for cc, nc, tt, ct, callers in self.stats.values():
      if callers:
        value = next(iter(callers.values()))
        subheader = isinstance(value, tuple)
        break
    if subheader:
      print(" "*name_size + "  ncalls  tottime  cumtime", file=self.stream)

  def display_call_line(self, name_size:int, source:Func, call_dict:Dict[Func,Any], arrow:str='->') -> None:
    print(fmt_func(source).ljust(name_size) + arrow, end=' ', file=self.stream)
    if not call_dict:
      print(file=self.stream)
      return
    clist = sorted(call_dict.keys())
    indent = ""
    for func in clist:
      name = fmt_func(func)
      value = call_dict[func]
      if isinstance(value, tuple):
        nc, cc, tt, ct = value
        if nc != cc:
            substats = '%d/%d' % (nc, cc)
        else:
            substats = '%d' % (nc,)
        substats = '%s %s %s  %s' % (substats.rjust(7+2*len(indent)),
                              f8(tt), f8(ct), name)
        left_width = name_size + 1
      else:
        substats = '%s(%r) %s' % (name, value, f8(self.stats[func][3]))
        left_width = name_size + 3
      print(indent*left_width + substats, file=self.stream)
      indent = " "

  def print_title(self) -> None:
    print('   ncalls  tottime  percall  cumtime  percall', end=' ', file=self.stream)
    print('filename:lineno(function)', file=self.stream)

  def display_line(self, func:Func) -> None:  # hack: should print percentages
    cc, nc, tt, ct, callers = self.stats[func]
    c = str(nc)
    if nc != cc:
      c = c + '/' + str(cc)
    print(c.rjust(9), end=' ', file=self.stream)
    print(f8(tt), end=' ', file=self.stream)
    if nc == 0:
      print(' '*8, end=' ', file=self.stream)
    else:
      print(f8(tt/nc), end=' ', file=self.stream)
    print(f8(ct), end=' ', file=self.stream)
    if cc == 0:
      print(' '*8, end=' ', file=self.stream)
    else:
      print(f8(ct/cc), end=' ', file=self.stream)
    print(fmt_func(func), file=self.stream)


def f8(x:float) -> str: return "%8.3f" % x

def get_func_name(func:Func) -> str:
  _, _, name = func
  return name

def fmt_func(func:Func) -> str:
  file, line, name = func
  if file == '~' and line == 0: # Special case for built-in functions.
    return name
  if file.startswith(std_prefix):
    file = '|' + file[len(std_prefix):]
  else:
    file = path_rel_to_current_or_abs(file)
  return f'{file}:{line}:{name}'

std_prefix = os.__file__[:-len('os.py')]

if __name__ == '__main__': main()
