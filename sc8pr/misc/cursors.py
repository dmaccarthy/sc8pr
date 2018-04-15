# Copyright 2015-2018 D.G. MacCarthy <http://dmaccarthy.github.io>
#
# This file is part of "sc8pr".
#
# "sc8pr" is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "sc8pr" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "sc8pr".  If not, see <http://www.gnu.org/licenses/>.


import pygame.cursors as pc
from pygame.cursors import arrow, diamond, broken_x, tri_left, tri_right

sizer_x = ((24,16),(12,8)) + pc.compile(pc.sizer_x_strings)
sizer_y = ((24,16),(12,8)) + pc.compile(pc.sizer_y_strings)
sizer_xy = ((24,16),(12,8)) + pc.compile(pc.sizer_xy_strings)
thickarrow = ((24,24),(0,0)) + pc.compile(pc.thickarrow_strings)

move = (16,16),(9,8),(1,128,3,192,7,224,1,128,1,128,17,136,49,140,127,254,127,254,49,140,17,136,1,128,1,128,7,224,3,192,1,128),(3,192,7,224,15,240,7,224,3,192,59,220,127,254,255,255,255,255,127,254,59,220,3,192,7,224,15,240,7,224,3,192)
text = (16,16),(4,7),(119,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,119,0),(119,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,119,0)
crosshair = (16,16),(8,8),(1,0,1,0,1,0,1,0,1,0,0,0,0,0,248,62,0,0,0,0,1,0,1,0,1,0,1,0,1,0,0,0),(1,0,1,0,1,0,1,0,1,0,0,0,0,0,248,62,0,0,0,0,1,0,1,0,1,0,1,0,1,0,0,0)
hand = (16,24),(6,1),(6,0,9,0,9,0,9,0,9,192,9,56,9,38,105,37,153,37,136,37,64,1,32,1,16,1,8,1,8,1,4,1,4,2,3,252,0,0,0,0,0,0,0,0,0,0,0,0),(6,0,15,0,15,0,15,0,15,192,15,184,15,254,111,253,255,253,255,255,127,255,63,255,31,255,15,255,15,255,7,255,7,254,3,252,0,0,0,0,0,0,0,0,0,0,0,0)
menu = (16,16),(3,2),(0,0,127,254,127,254,0,0,0,0,0,0,127,254,127,254,0,0,0,0,0,0,127,254,127,254,0,0,0,0,0,0),(255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,0,0,0,0)
cross = (16,16),(9,9),(0,0,192,3,96,6,48,12,24,24,12,48,6,96,3,192,1,128,3,192,6,96,12,48,24,24,48,12,96,6,192,3),(0,0,192,3,96,6,48,12,24,24,12,48,6,96,3,192,1,128,3,192,6,96,12,48,24,24,48,12,96,6,192,3)
circle = (16,16),(9,8),(3,192,14,112,24,24,48,12,96,6,96,6,192,3,192,3,192,3,96,6,96,6,48,12,24,24,14,112,3,192,0,0),(3,192,14,112,24,24,48,12,96,6,96,6,192,3,192,3,192,3,96,6,96,6,48,12,24,24,14,112,3,192,0,0)
