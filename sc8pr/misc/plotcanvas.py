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


from math import cos, sin, sqrt
import pygame
from sc8pr import Renderable, Graphic, Canvas, Image, CENTER
from sc8pr.text import Text
from sc8pr.geom import sigma, polar2d, transform2d, smallAngle, DEG
from sc8pr.shape import Arrow, Line
from sc8pr.misc import plot as oldPlot
from sc8pr.misc.plot import coordTr, _lrbt, locus


calc_lrbt = _lrbt


class PCanvas(Canvas):

    def __init__(self, size, lrbt, bg=None):
        super().__init__(size, bg)
        self._makeTr(lrbt)
    
    def _makeTr(self, lrbt=None):
        if lrbt: self._lrbt = lrbt = calc_lrbt(lrbt, *self.size)
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

    def flatten(self):
        self.config(bg=self.snapshot())
        self.purge()
        return self

    def grid(self, lrbt, interval, **kwargs):
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


# Labelling the axis...
#     self.points([(x, 0) for x in range(2, 10, 2)], "{0:d}", (0, -0.4))


class Locus(oldPlot.Locus):

    def __init__(self, data, param, **kwargs):
        self.data = data
        self.param = list(param)
        if len(param) < 3: self.param.append(100)
        self.vars = kwargs

    def draw(self, srf, snapshot=False):
        if snapshot: x0, y0 = 0, 0
        else: x0, y0 = self.canvas.rect.topleft
        px = getattr(self.canvas, "pix", None)
        d = self.data
        pts = d if type(d) in (list, tuple) else locus(d, self.param, **self.vars)
        if px: pts = (px(p) for p in pts)
        pts = [(x + x0, y + y0) for (x, y) in pts]
        if len(pts) > 1:
            wt = self.weight
            return pygame.draw.lines(srf, self.stroke, False, pts, wt).inflate(wt, wt)
        else: return pygame.Rect(0,0,0,0)


class VectorGrid(PCanvas):

    def __init__(self, width, lrbt, grid=1, margin=1, bg=None):

        # Create plot canvas
        tmp = [lrbt[i] + (1 if i % 2 else -1) * margin for i in range(4)]
        height = round(width * (tmp[3] - tmp[1]) / (tmp[2] - tmp[0]))
        super().__init__((width, height), tmp, bg)
        
        # Draw grid and axes
        if grid: self.grid(lrbt, (grid, grid)).axis(x=lrbt[:2], y=lrbt[2:])


class Vector(Renderable):
    plot = None
    tail = 0, 0
    stroke = "red"
    weight = 3
    arrowShape = 16, 10
    contains = Graphic.contains

    def __init__(self, mag=None, direction=0, xy=None):
        if mag is None:
            self.mag, self.dir = polar2d(*xy)
        else:
            if mag < 0:
                self.dir = direction + 180
                self.mag = -mag
            else:
                self.dir = direction
                self.mag = mag
            self.dir = smallAngle(self.dir)

    def __str__(self):
        x, y = self.xy
        return "<{} {:.3g} @ {:.1f} ({:.3g}, {:.3g})>".format(type(self).__name__, self.mag, self.dir, x, y)

    @property
    def anchor(self): return CENTER

    @property
    def angle(self):
        p = self.plot
        return self.dir if (p is None or p.clockwise) else -self.dir

    @angle.setter
    def angle(self, a):
        p = self.plot
        self.dir = smallAngle(a if (p is None or p.clockwise) else -a)

    def rotate(self, angle, xy=None):
        if xy is None: xy = self.middle
        self.tail = transform2d(self.tail, rotate=angle, shift=xy, preShift=True)
        self.dir += angle

    @property
    def xy(self): return self.x, self.y

    @property
    def x(self): return self.mag * cos(self.dir * DEG)

    @property
    def y(self): return self.mag * sin(self.dir * DEG)

    def proj(self, u):
        "Return projection onto a vector or direction"
        u = Vector(1, u.dir if isinstance(u, Vector) else u)
        return (u * (self * u)).config(plot=self.plot)

    def __add__(self, other):
        xy = sigma(self.xy, other.xy)
        return Vector(xy=xy).config(plot=self.plot)

    def __sub__(self, other):
        return self + other * -1

    def __mul__(self, other):
        if isinstance(other, Vector):
            x1, y1 = self.xy
            x2, y2 = other.xy
            return x1 * x2 + y1 * y2
        else:
            return Vector(other * self.mag, self.dir).config(plot=self.plot)

    def __truediv__(self, x):
        return Vector(self.mag / x, self.dir).config(plot=self.plot)

    def shift(self, dx=0, dy=0):
        tx, ty = self.tail
        self.tail = tx + dx, ty + dy

    @property
    def middle(self):
        tx, ty = self.tail
        x, y = self.xy
        return tx + x/2, ty + y/2

    @middle.setter
    def middle(self, xy):
        cx, cy = self.middle
        self.shift(xy[0] - cx, xy[1] - cy)

    @property
    def tip(self):
        tx, ty = self.tail
        x, y = self.xy
        return tx + x, ty + y

    @tip.setter
    def tip(self, xy):
        tx, ty = self.tip
        self.shift(xy[0] - tx, xy[1] - ty)

    @property
    def unit(self):
        p = self.plot
        return 1 if p is None else p.unit

    @property
    def pos(self):
        c = self.middle
        p = self.plot
        return c if p is None else p.pix(c)

    @pos.setter
    def pos(self, xy):
        p = self.plot
        self.middle = xy if p is None else p.unpix(xy)

    def render(self):
        l = self.mag * self.unit
        shape = self.arrowShape
        if type(shape) is dict:
            if shape["fixed"]:
                shape = shape.copy()
                shape["width"] /= l
                shape["head"] /= l
            del shape["fixed"]
            a = Arrow(l, **shape).config(fill=self.fill, stroke=self.stroke, weight=self.weight)
        else:
            dx, dy = shape
            cv = Canvas((l, 2 * dy))
            y = cv.center[1]
            cv += Line((0, y), (l, y)).config(stroke=self.stroke, weight=self.weight)
            cv += Line((l - dx, y - dy), (l, y)).config(stroke=self.stroke, weight=self.weight)
            cv += Line((l - dx, y + dy), (l, y)).config(stroke=self.stroke, weight=self.weight)
            a = cv.snapshot()
        return a.image

    def style(self, n=1):
        "Preset drawing styles"
        self.config(fill="red", stroke="black", weight=1)
        if n == 1:
            self.arrowShape = {"width": 12, "head": 16, "flatness": 2, "fixed": True}
        else:
            self.arrowShape = {"width": 0.1, "head": 0.1, "flatness": 2, "fixed": False}
        return self
