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


from math import sqrt
import pygame
from sc8pr import Image, Canvas
from sc8pr.shape import Line
from sc8pr.text import Text
from sc8pr.misc import plot as oldPlot
from sc8pr.misc.plot import coordTr, _lrbt, locus


class Plot(Canvas):

    def __init__(self, size, lrbt, bg=None):
        super().__init__(size, bg)
        self._makeTr(lrbt)
    
    def _makeTr(self, lrbt=None):
        if lrbt: self._lrbt = lrbt = _lrbt(lrbt, *self.size)
        else: lrbt = self._lrbt
        self.pix = px = coordTr(lrbt, self.size)
        self.unpix = coordTr(lrbt, self.size, True)
        p0 = px((0, 0))
        p1 = px((1, 1))
        p0, p1 = p1[0] - p0[0], p1[1] - p0[1]
        self._units = p0, p1, sqrt(abs(p0 * p1)), p0 * p1 > 0

    @property
    def left(self): return self._lrbt[0]

    @property
    def right(self): return self._lrbt[1]

    @property
    def bottom(self): return self._lrbt[2]

    @property
    def top(self): return self._lrbt[3]

    @property
    def clockwise(self): return self._units[3]

    @property
    def units(self): return self._units[:2]

    @property
    def unit(self): return self._units[2]

    @property
    def size(self): return self._size

    @size.setter
    def size(self, size): self.resize(size)

    def resize(self, size):
        super().resize(size)
        self._makeTr()

    def freeze(self):
        self.config(bg=self.snapshot())
        self.purge()
        return self

    def gridlines(self, lrbt, interval, **kwargs):
        style = {"weight":1, "stroke":"lightgrey"}
        style.update(kwargs)
        dx, dy = interval
        x0, x1, y0, y1 = lrbt
        px = self.pix
        if dx:
            x = x0
            while x < x1 + dx / 2:
                self += Line(px((x, y0)), px((x, y1))).config(**style)
                x += dx
        if dy:
            while y0 < y1 + dy / 2:
                self += Line(px((x0, y0)), px((x1, y0))).config(**style)
                y0 += dy
        return self

    def axis(self, x=None, y=None, **kwargs):
        style = {"weight":2, "stroke":"black"}
        style.update(kwargs)
        px = self.pix
        if x: self += Line(px((x[0], 0)), px((x[1], 0))).config(**style)
        if y: self += Line(px((0, y[0])), px((0, y[1]))).config(**style)
        return self

    def points(self, points, markers, shift=(0, 0), **kwargs):
        i = 0
        dx, dy = shift
        px = self.pix
        for x, y in points:
            if type(markers) is str:
                gr = Text(markers.format(x, y)).config(**kwargs)
            else:
                try: gr = markers[i]
                except: gr = Image(markers)
            self += gr.config(pos=px((x + dx, y + dy)))
            i += 1
        return self

    def locus(self, data, param=None, **kwargs):
        locus = Locus(data, param, **kwargs)
        self += locus
        return locus


class Locus(oldPlot.Locus):

    def __init__(self, data, param, **kwargs):
        self.data = data
        self.param = param
        self.vars = kwargs

    def draw(self, srf, snapshot=False):
        if snapshot: x0, y0 = 0, 0
        else: x0, y0 = self.canvas.rect.topleft
        px = self.canvas.pix
        d = self.data
        pts = d if type(d) in (list, tuple) else locus(d, self.param, **self.vars)
        pts = [px(p) for p in pts]
        pts = [(x + x0, y + y0) for (x, y) in pts]
        if len(pts) > 1:
            wt = self.weight
            return pygame.draw.lines(srf, self.stroke, False, pts, wt).inflate(wt, wt)
        else: return pygame.Rect(0,0,0,0)
