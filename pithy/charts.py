from .svg import *
from io import StringIO
from typing import *

class XYChart:
  def __init__(self, *series:Tuple[str, Iterable[Tuple]],
   title:str=None,
   x_label:str=None, y_label:str=None,
   w:int=None, h:int=None,
   plot_w:int=None, plot_h:int=None,
   x_min:int=None, x_max:int=None, y_min:int=None, y_max:int=None,
   title_height:int=None,
   label_width:int=None, label_height:int=None,
   legend_width:int=None, # TODO: legend_height would imply that the legend is at bottom.
   ) -> None:
    self.series = {k : list(v) for k, v in series}

    #take smallest_x and largest_x value from data if x_min or y_min is undefined
    min_x:float = 0
    max_x:float = 1
    min_y:float = 0
    max_y:float = 1
    for k,s in self.series.items():
      for x,y in s:
        min_x = min(x, min_x)
        max_x = max(x, max_x)
        min_y = min(y, min_y)
        max_y = max(y, max_y)
    if(x_min == None): x_min = min_x
    if(y_min == None): y_min = min_y
    if(x_max == None): x_max = max_x
    if(y_max == None): y_max = max_y
    self.x_min = x_min
    self.x_max = x_max
    self.y_min = y_min
    self.y_max = y_max
    x_range:float = x_max - x_min
    y_range:float = y_max - y_min
    self.svg_width = w
    self.svg_height = h
    self.label_height = label_height
    self.label_width = label_width
    self.legend_width = legend_width
    self.title_height = title_height
    self.title = title
    self.x_label = x_label
    self.y_label = y_label

    x_scale = ((self.svg_width - 10) - (self.legend_width + self.label_width + 10))/x_range
    y_scale = ((self.svg_height - self.title_height)-(self.label_height+10))/y_range
    scaled_min_x=0
    scaled_min_y=0
    for k,s in self.series.items():
      for x,y in s:
        scaled_min_x = min(x*x_scale, scaled_min_x)
        scaled_min_y = min(y*y_scale, scaled_min_y)
    for k,s in self.series.items():
      temp_list = []
      for x,y in s:
        temp_list.append(((x*x_scale)-scaled_min_x, (y*y_scale)-scaled_min_y))
      self.series[k] = temp_list



  def render(self, file=None) -> str:
    colors:List = ['#EF7F6D', '#F78398', '#E893C4', '#C2AAE5', '#89C2F3', '#49D5E9', '#38E2CA', '#70E9A0', '#AFEB77', '#EFE55D']
    if file is None:
      file = StringIO()
    chart_x_min:int = self.legend_width + self.label_width + 10
    chart_x_max:int = self.svg_width - 10
    chart_y_min:int = self.label_height+10
    chart_y_max:int = self.svg_height - self.title_height
    with SvgWriter(file, w=self.svg_width, h=self.svg_height) as svg:
      y_range = chart_y_max - chart_y_min
      #draw graph
      svg.rect(pos=(chart_x_min, chart_y_min), size=(chart_x_max-chart_x_min, chart_y_max - chart_y_min), stroke=None, fill='#fafafa')
      transform_x =  700
      color_picker = 0
      with svg.g(transform=f'translate({chart_x_min} {chart_y_max}) scale(1 -1) '):
        for i in range(1,5):
            svg.line((0, (y_range/5)*i), (chart_x_max-70, (y_range/5)*i), stroke='#BBCCDD' )
            with svg.g(transform=' scale(1 -1) '):
              svg.text(text=((self.y_max-self.y_min)/5*i), x = -40, y = -((y_range/5)*i) + 6, style="color:black") #max y
        for k,s in self.series.items(): #each series
          for p in s:
            print(p)
          svg.polyline((p for p in s), style=f'fill:none;stroke:{colors[color_picker]};stroke-width:1')
          color_picker = (1+color_picker) % 10
          print(color_picker)

      #text
      svg.text(text=self.title, x=self.svg_width/1.9, y = self.label_height*1.4, style=f"color:black;font-size:{self.title_height}") #title
      svg.text(text=self.y_label, x=0, y = self.svg_height/2, style="color:black") #x axis
      svg.text(text=self.x_label, x=self.svg_width/2, y = self.svg_height, style="color:black") #y axis
      svg.text(text=str(self.x_min), x = chart_x_min, y = (chart_y_max+15), style="color:black") #min x
      svg.text(text=str(self.y_min), x = chart_x_min-10, y = (chart_y_max), style="color:black") #min y
      svg.text(text=str(self.x_max), x = chart_x_max-20, y = (chart_y_max+15), style="color:black") #max x
      svg.text(text=str(self.y_max), x = chart_x_min-25, y = (chart_y_min+10), style="color:black") #max y
      #horizontal lines




      pass
