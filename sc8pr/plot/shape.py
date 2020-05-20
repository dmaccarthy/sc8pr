# Copyright 2015-2020 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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

from math import sin, cos
import pygame
from sc8pr import Canvas, Graphic, Renderable
from sc8pr.shape import Line, Arrow
from sc8pr.geom import sigma, DEG, transform2d, smallAngle, polar2d
from sc8pr.misc.plot import locus, Locus
from sc8pr.plot import _PObject


class PLocus(Locus):
    scrollable = False

    def __init__(self, data, param=None, **kwargs):
        self.data = data
        if param is not None:
            self.param = list(param)
            if len(param) < 3: self.param.append(100)
        self.vars = kwargs

    def draw(self, srf, snapshot=False):
        if snapshot: x0, y0 = 0, 0
        else: x0, y0 = self.canvas.rect.topleft
        px = self.canvas.px
        d = self.data
        pts = d if type(d) in (list, tuple) else locus(d, self.param, **self.vars)
        if px: pts = (px(*p) for p in pts)
        pts = [(x + x0, y + y0) for (x, y) in pts]
        if len(pts) > 1:
            wt = self.weight
            return pygame.draw.lines(srf, self.stroke, False, pts, wt).inflate(wt, wt)
        else: return pygame.Rect(0,0,0,0)


class PVector(_PObject, Renderable):
    autoPositionOnResize = scrollable = False
    tail = 0, 0
    stroke = "red"
    weight = 3
    arrowShape = 16, 10
    contains = Graphic.contains
    _plot = None

    def __init__(self, mag=None, theta=0, xy=None):
        if mag is None:
            self.mag, self.theta = polar2d(*xy)
        else:
            if mag < 0:
                self.theta = theta + 180
                self.mag = -mag
            else:
                self.theta = theta
                self.mag = mag
            self.theta = smallAngle(self.theta)

    def __str__(self):
        x, y = self.xy
        return "<{} {:.3g} @ {:.1f} ({:.3g}, {:.3g})>".format(type(self).__name__, self.mag, self.theta, x, y)

    def rotate(self, angle, xy=None):
        if xy is None: xy = self.csPos
        self.tail = transform2d(self.tail, rotate=angle, shift=xy, preShift=True)
        self.theta += angle

    @property
    def xy(self): return self.x, self.y

    @property
    def x(self): return self.mag * cos(self.theta * DEG)

    @property
    def y(self): return self.mag * sin(self.theta * DEG)

    def proj(self, u):
        "Return projection onto a vector or direction"
        u = PVector(1, u.theta if isinstance(u, PVector) else u)
        return (u * (self * u))#.config(_plot=self._plot)

    def components(self, **kwargs):
        x = self.proj(0).config(tail=self.tail, **kwargs)
        y = self.proj(90).config(tip=self.tip, **kwargs)
        return [x, y]

    def __add__(self, other):
        xy = sigma(self.xy, other.xy)
        return PVector(xy=xy)#.config(_plot=self._plot)

    def __sub__(self, other):
        return self + other * -1

    def __mul__(self, other):
        if isinstance(other, PVector):
            x1, y1 = self.xy
            x2, y2 = other.xy
            return x1 * x2 + y1 * y2
        else:
            return PVector(other * self.mag, self.theta)#.config(_plot=self._plot)

    def __truediv__(self, x):
        return PVector(self.mag / x, self.theta)#.config(_plot=self._plot)

    def shift(self, dx=0, dy=0):
        tx, ty = self.tail
        self.tail = tx + dx, ty + dy

    @property
    def csPos(self):
        tx, ty = self.tail
        x, y = self.xy
        return tx + x/2, ty + y/2

    @csPos.setter
    def csPos(self, xy):
        cx, cy = self.csPos
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

    def render(self):
        l = self.mag * self.canvas.unit
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
