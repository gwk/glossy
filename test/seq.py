#!/usr/bin/env python3

from utest import *
from pithy.seq import *


utest_seq([], seq_int_ranges, [])
utest_seq([(0, 1), (2, 5)], seq_int_ranges, [0, (2,3), range(3, 5)])

utest_seq_exc(ValueError(0), group_seq_by_heads, [0, 1, 2, 3, 4], is_head=lambda x: x % 2)

utest_seq([[1, 2], [3, 4]], group_seq_by_heads, [0, 1, 2, 3, 4], is_head=lambda x: x % 2, headless=HeadlessMode.drop)

utest_seq([[0], [1, 2], [3, 4]], group_seq_by_heads, [0, 1, 2, 3, 4], is_head=lambda x: x % 2, headless=HeadlessMode.keep)
