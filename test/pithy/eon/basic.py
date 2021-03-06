#!/usr/bin/env python3
# Dedicated to the public domain under CC0: https://creativecommons.org/publicdomain/zero/1.0/.

from pithy.eon import *
from utest import *


def parse(text:str) -> Any:
  return parse_eon(path='<test>', text=text, to=object)


utest(None, parse, '')


utest(
  { 'a': 'b',
    'c': {
      1: 2,
      3: 4 },
    'd': [
      5,
      6 ] },
  parse,
  '''
a: b
c:
  1: 2
  3: 4

d:
  5

  6

''')


utest(
  [{ 1 : 2,
    3 : [ 'a', 'b' ] }],
  parse,
  '''
~ 1: 2
  3: -
    a
    b
''')


# List inline / multiline combinations.
utest([[1]], parse, '- 1\n')
utest([[1]], parse, '-\n  1\n')
utest([[1, 2]], parse, '- 1\n  2\n')

# Dict inline / multiline combinations.
utest([{1:2}], parse, '~ 1:2\n')
utest([{1:2}], parse, '~\n  1:2\n')
utest([{1:2, 3:4}], parse, '~ 1:2\n  3:4\n')
