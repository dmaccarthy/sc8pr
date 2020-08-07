# Copyright 2015-2020 D.G. MacCarthy <http://dmaccarthy.github.io>
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


from math import hypot, atan2, pi
import pygame
from sc8pr import Renderable, Image

DEG = pi / 180


def hsva(h, s, v=100, a=100):
    "Create a color from HSVA values"
    c = pygame.Color(0, 0, 0)
    c.hsva = h, min(100, s), v, a
    return c

def hsvBox(color, hue=None, sat=None, val=None):
    "Check if color is within specified color wheel 'box'"
    h, s, v = color.hsva[:3]
    return (hue is None or _between(h, *hue)) and (sat is None
        or _between(s, *sat)) and (val is None or _between(v, *val))

def _between(x, x0, x1):
    if x0 < x1: return x0 <= x and x <= x1
    else: return x >= x0 or x <= x1

def hs_surface(size=(100,100), v=100, wheel=False):
    "Create a hue-saturation color array"
    width, height = size
    srf = pygame.Surface(size, pygame.SRCALPHA)
    pxa = pygame.PixelArray(srf)
    f = 100 / (height - 1)
    xc, yc = (width - 1) / 2, (height - 1) / 2
    for c in range(width):
        if wheel:
            pxc = pxa[c]
            for r in range(height):
                x = (c - xc) / xc
                y = (r - yc) / yc
                s = 100 * hypot(x, y)
                if s <= 100:
                    h = atan2(y, x) / DEG
                    pxc[r] = hsva(h + 360 if h < 0 else h, s, v)
        else:
            h = 360 * c / width
            pxa[c] = [hsva(h, r * f, v) for r in range(height)]
    return srf


class HSV(Renderable):
    "Graphic to render an HSV color wheel or rectangle"
    _size = 128, 128
    val = 100
    wheel = True

    def render(self):
        size = [round(x) for x in self._size]
        return hs_surface(size, self.val, self.wheel)

    contains = Image.contains
