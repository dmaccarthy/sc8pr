# Copyright 2015-2023 D.G. MacCarthy <http://dmaccarthy.github.io>
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

import pygame
from pygame.draw import circle, polygon
from math import hypot, ceil, pi, cos, sin
from sc8pr.util import surface, rgba
from sc8pr.effect import Effect
from sc8pr.shape import Polygon

TWO_PI = 2.0 * pi


class Stamp(Effect):
    _fill = rgba("white")
    special_flags = pygame.BLEND_RGBA_MIN

    def apply(self, img, n=0):
        img = surface(img, True)
        if n <= 0 or n >= 1: return self.nofx(img, n)
        srf = surface(self.get_stamp(n, img.get_size()))
        srf.blit(img, (0, 0), special_flags=self.special_flags)
        return srf


class Pupil(Stamp):
    sides = None
    center = 0.5, 0.5

    def get_stamp(self, t, size):
        w, h = size
        x, y = self.center
        x = (w-1) * x
        y = (h-1) * (1-y)
        r = 1 + ceil(t * hypot(max(x, w-x), max(y, h-y)))
        srf = pygame.Surface(size, pygame.SRCALPHA)
        if self.sides is None: circle(srf, self._fill, (x, y), r)
        else:
            angle = 90 - 180 / self.sides
            a = 2 * pi / self.sides
            r /= cos(a/2)
            pts = [(r*cos(i*a), r*sin(i*a)) for i in range(self.sides)]
            poly = Polygon(pts, (0,0)).config(angle=angle).config(pos=(x, y))
            polygon(srf, self._fill, poly.vertices)
        return srf


class Spiral(Stamp):
    cycles = 5
    clockwise = True
    _vert = 100

    def points(self, t):
        n = self.cycles
        v = self._vert
        cw = self.clockwise
        x = 1 / n
        angleEnd = TWO_PI * n * (t % x)
        first = t < x
        if first: yield 0.0, 0.0
        for i in range(v + 1):
            i /= v
            if first:
                a = i * angleEnd
                r = x + t * i
            else:
                a = angleEnd + i * TWO_PI
                r = t + x * i
            if cw: a = -a
            yield r*cos(a), r*sin(a)

    def get_stamp(self, t, size):
        w, h = size
        srf = pygame.Surface(size, pygame.SRCALPHA)
        poly = Polygon(self.points(t), (0,0))
        poly.transform(scale=(w/1.4, h/1.4)).config(pos=(w/2, h/2))
        polygon(srf, self._fill, poly.vertices)
        return srf
