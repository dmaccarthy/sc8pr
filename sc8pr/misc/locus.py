# Copyright 2015-2017 D.G. MacCarthy <http://dmaccarthy.github.io>
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
from sc8pr import Renderable, Image
from sc8pr.shape import Shape


def locus(func, t0, t1, steps, **params):
    "Generate a parameterized sequence of 2D points"
    for i in range(steps + 1):     
        try:
            x = t0 + i * (t1 - t0) / steps
            y = func(x, **params)
            yield y if type(y) in (tuple, list) else (x, y)
        except: pass


class Locus(Renderable, Shape):
    bg = None
    params = {}
    steps = 100
    _coords = None
    circle = 0
    limits = None

    def __init__(self, size, func):
        self._size = size
        self.func = func

    @property
    def size(self): return self._size

    @size.setter
    def size(self, size): self.resize(size)

    @property
    def coords(self): return self._coords

    @coords.setter
    def coords(self, lrbt):
        assert len(lrbt) == 4
        self._coords = lrbt
        self.stale = True

    def render(self):
        srf = Image(self._size, self.bg).image
        prev = None
        if self.limits is None:
            lims = [0, self._size[0]] if self._coords is None else self._coords[:2]
        else: lims = self.limits 
        pts = locus(self.func, *lims, self.steps, **self.params)
        if self._coords:
            l, r, b, t = self._coords
            sx, sy = self._size
            sx /= (r - l)
            sy /= (b - t)
            dx = sx * l
            dy = sy * t
            transform = lambda p: (sx * p[0] - dx, sy * p[1] - dy)
        else: transform = lambda p: p
        wt = self.weight
        circ = self.circle
        color = self._stroke
        for p in pts:
            p = transform(p)
            q = round(p[0]), round(p[1])
            if circ: pygame.draw.circle(srf, color, q, circ)
            if wt and prev: pygame.draw.line(srf, color, prev, p, wt)
            prev = p
        return srf

    def resize(self, size):
        self._size = size
        self.stale = True

    contains = Image.contains
