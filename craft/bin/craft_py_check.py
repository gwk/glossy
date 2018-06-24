#!/usr/bin/env python3
# Dedicated to the public domain under CC0: https://creativecommons.org/publicdomain/zero/1.0/.

from pithy.ansi import *
from pithy.io import *
from pithy.lex import Lexer
from pithy.task import runCO


def main():
  c, o = runCO(['mypy', *argv[1:]])
  for token in lexer.lex(o):
    s = token[0]
    kind = token.lastgroup
    if kind == 'location' and '/' not in s and '<' not in s:
      s = './' + s
    try: color = colors[kind]
    except KeyError: outZ(s)
    else: outZ(color, s, RST)
    stdout.flush()


lexer = Lexer(invalid='invalid', patterns=dict(
  newline   = r'\n',
  location  = r'[^:\n]+:\d+:(\d+:)?',
  error     = r'error:',
  warning   = r'warning:',
  note      = r'note:',
  quoteD    = r'"[^"]*"',
  quoteS    = r"'[^']*'",
  text      = r'.+?',
))

colors = {
  'invalid'   : INVERT,
  'location'  : TXT_L,
  'error'     : TXT_R,
  'warning'   : TXT_Y,
  'note'      : TXT_L,
  'quoteD'    : TXT_C,
  'quoteS'    : TXT_C,
}

if __name__ == '__main__': main()
