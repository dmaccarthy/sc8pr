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

from math import cos, sin, sqrt, ceil
import pygame
from sc8pr import Sketch, Renderable, Canvas, Image #, Graphic, CENTER
from sc8pr.text import Text
from sc8pr.geom import smallAngle #, sigma, polar2d, transform2d, dist, DEG
from sc8pr.shape import Line, Polygon #, Shape, Arrow
from sc8pr.misc.plot import _lrbt #, locus, Locus
from sc8pr.util import mix

calc_lrbt = _lrbt


class Plotable:
    _plot = True
    autoPositionOnResize = False

    @property
    def plot(self):
        p = self._plot
        if p is True:
            p = getattr(self, "canvas", None)
            if not isinstance(p, CoordinateSystem): p = None
        return p

    @plot.setter
    def plot(self, p): self._plot = p

    @property
    def angle(self):
        p = self.plot
        return self.dir if (p is None or p.clockwise) else -self.dir

    @angle.setter
    def angle(self, a):
        p = self.plot
        self.dir = smallAngle(a if (p is None or p.clockwise) else -a)

    @property
    def unit(self):
        p = self.plot
        return 1 if p is None else p.unit

    @property
    def pos(self):
        c = self.plotPos
        p = self.plot
        return c if p is None else p.pix(*c)

    @pos.setter
    def pos(self, xy):
        p = self.plot
        self.plotPos = xy if p is None else p.unpix(*xy)


def _autoSize(lrbt, width):
    return width, round(width * (lrbt[3] - lrbt[2]) / (lrbt[1] - lrbt[0]))

def _str2gr(text, x, y, **kwargs):
    xy = dict(x=x, y=y)
    return Text(text.format(**xy)).config(**kwargs)

def _coord(lrbt, size, invert=False):
    "Create a transformation for the given coordinate system"
    if len(lrbt) != 4: lrbt = _lrbt(lrbt, *size)
    l, r = lrbt[:2]
    sx = size[0] / (r - l)
    dx = sx * l
    b, t = lrbt[2:]
    sy = size[1] / (b - t)
    dy = sy * t
    if invert:
        return lambda *p: ((p[0] + dx) / sx, (p[1] + dy) / sy)
    else:
        return lambda *p: (sx * p[0] - dx, sy * p[1] - dy)


class CoordinateSystem:

    def coords(self, lrbt=None, size=None):
        first = not hasattr(self, "_lrbt")
        if first:
            if size is None: size = self.size
            elif type(size) is int: size = _autoSize(lrbt, size)
            lrbt = calc_lrbt(lrbt, *size)
        else:
            lrbt = self._lrbt
            size = self.size

        self.pix = px = _coord(lrbt, size)
        self.unpix = ux = _coord(lrbt, size, True)
        p0 = px(0, 0)
        p1 = px(1, 1)
        p0, p1 = p1[0] - p0[0], p1[1] - p0[1]
        self._units = p0, p1, sqrt(abs(p0 * p1)), p0 * p1 > 0

        if first:
            x0, y1 = ux(0, 0)
            x1, y0 = ux(*size)
            self._lrbt = x0, x1, y0, y1
        elif isinstance(self, Canvas):
            for gr in self.instOf(Renderable): gr.stale = True

    __init__ = coords

    def transform(self, pts, **kwargs):
        tr = self.unpix if kwargs.get("invert") else self.pix
        for pt in pts: yield(tr(*pt))

    @property
    def left(self): return self._lrbt[0]

    @property
    def right(self): return self._lrbt[1]

    @property
    def bottom(self): return self._lrbt[2]

    @property
    def top(self): return self._lrbt[3]

    @property
    def bottomleft(self):
        c = self._lrbt
        return c[0], c[2]

    @property
    def bottomright(self):
        c = self._lrbt
        return c[1], c[2]

    @property
    def topright(self):
        c = self._lrbt
        return c[1], c[3]

    @property
    def topleft(self):
        c = self._lrbt
        return c[0], c[3]

    @property
    def middle(self):
        c = self._lrbt
        return (c[0] + c[1]) / 2, (c[2] + c[3]) / 2

    @property
    def clockwise(self): return self._units[3]

    @property
    def units(self): return self._units[:2]

    @property
    def unit(self): return self._units[2]

    @property
    def origin(self): return self.pix(0, 0)

    def gridlines(self, lrbt, interval, axis=None, **kwargs):
        style = {"weight":1, "stroke":"lightgrey"}
        style.update(kwargs)
        dx, dy = interval
        x0, x1, y0, y1 = lrbt
        px = self.pix
        if dx:
            x = x0
            while x < x1 + dx / 2:
                self += Line(px(x, y0), px(x, y1)).config(**style)
                x += dx
        if dy:
            while y0 < y1 + dy / 2:
                self += Line(px(x0, y0), px(x1, y0)).config(**style)
                y0 += dy
        return self if axis is None else self.axis(lrbt, **axis)

    def axis(self, lrbt, **kwargs):
        style = {"weight":2, "stroke":"black"}
        style.update(kwargs)
        px = self.pix
        x, y = lrbt[:2], lrbt[2:]
        if x: self += Line(px(x[0], 0), px(x[1], 0)).config(**style)
        if y: self += Line(px(0, y[0]), px(0, y[1])).config(**style)
        return self

    def graph(self, points, markers, shift=(0, 0), **kwargs):
        i = 0
        dx, dy = shift
        px = self.pix
        for x, y in points:
            t = type(markers)
            if t in (int, float):
                if True or y > 0:
                    dx = markers / 2
                    pts = [(x-dx, 0), (x-dx, y), (x+dx, y), (x+dx, 0)]
                    bar = Polygon(self.transform(pts)).config(**kwargs)
                    if bar.height >= 1: self += bar
            else:
                if t is str: gr = _str2gr(markers, x, y, **kwargs)
                else:
                    try:
                        gr = markers[i]
                        if type(gr) is str: gr = _str2gr(gr, x, y, **kwargs)
                    except: gr = Image(markers)
                self += gr
                gr.config(pos=px(x + dx, y + dy))
            i += 1
        return self

    def mix(self, x, y, markers, shift=(0, 0), **kwargs):
        return self.graph(mix(x, y), markers, shift, **kwargs)

    def zip(self, x, y, markers, shift=(0, 0), **kwargs):
        return self.graph(zip(x, y), markers, shift, **kwargs)


class PCanvas(Canvas, CoordinateSystem):

    def __init__(self, size, lrbt, bg=None):
        if type(size) is int: size = _autoSize(lrbt, size)
        super().__init__(size, bg)
        CoordinateSystem.coords(self, lrbt)

    def resize(self, size):
        super().resize(size)
        CoordinateSystem.coords(self)

    def coords(self, lrbt):
        delattr(self, "_lrbt")
        CoordinateSystem.coords(self, lrbt, self.size)
        

class PSketch(Sketch, CoordinateSystem):
    coords = PCanvas.coords

    def __init__(self, size, lrbt):
        if type(size) is int: size = _autoSize(lrbt, size)
        super().__init__(size)
        CoordinateSystem.coords(self, lrbt, size)

    def resize(self, size, mode=None):
        super().resize(size, mode)
        CoordinateSystem.coords(self, size=size)
