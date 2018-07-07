# Dedicated to the public domain under CC0: https://creativecommons.org/publicdomain/zero/1.0/.

'''
HTML writer.
'''

from sys import stdout
from html import escape as html_escape
from types import TracebackType
from typing import Any, ContextManager, Dict, List, Optional, Sequence, TextIO, Tuple, Type, Union, Iterable, cast
from .num import Num, NumRange
from .xml import XmlAttrs, XmlWriter, add_opt_attrs, esc_xml_attr, esc_xml_text, _Self
from .svg import *


Dim = Union[int, float, str]
Vec = Tuple[Num, Num]
VecOrNum = Union[Vec, Num]
PathCommand = Tuple

ViewBox = Union[None, Vec, Tuple[Num, Num, Num, Num], Tuple[Vec, Vec]] # TODO: currently unused.


class HtmlWriter(XmlWriter):
  '''
  HtmlWriter is a ContextManager class that outputs SVG code to a file (stdout by default).
  Like its parent class XmlWriter, it uses the __enter__ and __exit__ methods to automatically output open and close tags.
  '''

  def __init__(self, file:TextIO=None, attrs:XmlAttrs=None, **extra_attrs:Any) -> None:
    super().__init__(tag='html', file=file, attrs=attrs, **extra_attrs)

  def __enter__(self:_Self) -> _Self:
    self.write('<!DOCTYPE html>')
    return super().__enter__()

  def body(self, **attrs:Any) -> XmlWriter:
    return self.sub('body', attrs=attrs)

  def br(self) -> None: self.leaf('br', attrs=None)

  def div(self, **attrs:Any) -> XmlWriter: return self.sub('div', attrs=attrs)

  def head(self, **attrs:Any) -> XmlWriter: return self.sub('head', attrs=attrs)

  def h1(self, text:str, **attrs:Any) -> None: self.leaf_text('h1', attrs=attrs, text=text)
  def h2(self, text:str, **attrs:Any) -> None: self.leaf_text('h2', attrs=attrs, text=text)
  def h3(self, text:str, **attrs:Any) -> None: self.leaf_text('h3', attrs=attrs, text=text)
  def h4(self, text:str, **attrs:Any) -> None: self.leaf_text('h4', attrs=attrs, text=text)
  def h5(self, text:str, **attrs:Any) -> None: self.leaf_text('h5', attrs=attrs, text=text)
  def h6(self, text:str, **attrs:Any) -> None: self.leaf_text('h6', attrs=attrs, text=text)

  def hr(self) -> None: self.leaf('hr', attrs=None)

  def meta(self, **attrs:Any) -> XmlWriter: return self.sub('meta', attrs=attrs)

  def p(self, **attrs:Any) -> XmlWriter: return self.sub('p', attrs=attrs)

  def style(self, *styles:str, **attrs:Any) -> None:
    self.leaf_text('style', attrs=attrs, text='\n'.join(styles))

  def svg(self, pos:Vec=None, size:VecOrNum=None, *, x:Dim=None, y:Dim=None, w:Dim=None, h:Dim=None,
   vx:Num=None, vy:Num=None, vw:Num=None, vh:Num=None, **attrs:Any) -> SvgWriter:
    return SvgWriter(file=self.file, pos=pos, size=size, x=x, y=y, w=w, h=h, vx=vx, vy=vy, vw=vw, vh=vh, **attrs)

  def title(self, title:str, **attrs:Any) -> None:
    self.leaf_text('title', attrs=attrs, text=title)
