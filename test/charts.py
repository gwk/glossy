from sys import stdout
from pithy.charts import *


chart = XYChart(
  ('A', [(-20,0), (100,100), (120,400)]),
  ('B', [(100,1), (150,200)]), w=500, h=300, title_height=20, label_height=10, label_width=20, legend_width=40,
  title='Test Chart', x_label='x axis', y_label='y axis'
)

chart.render(file=stdout)