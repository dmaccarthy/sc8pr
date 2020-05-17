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


from math import cos, sin, ceil
import pygame
from sc8pr import Renderable, Graphic, Canvas, CENTER
from sc8pr.geom import sigma, polar2d, transform2d, smallAngle, dist, DEG
from sc8pr.shape import Arrow, Line, Shape
from sc8pr.misc.plot import locus, Locus
from sc8pr.plot import Plotable


class PCircle(Plotable, Renderable, Shape):

    def __init__(self, r):
        self.plotPos = 0, 0
        self.r = r

    @property
    def angle(self): return 0

    @property
    def radius(self): return ceil(self.r * self.unit)

    @property
    def size(self):
        d = 2 * self.radius
        return d, d

    @size.setter
    def size(self, size): self.resize(size) 
  
    def resize(self, size):
        self.r = max(size) / 2 / self.unit
        self.stale = True
        return self

    def render(self):
        srf = pygame.Surface(self.size, pygame.SRCALPHA)
        x, y = self.center
        x = round(x)
        y = round(y)
        r = self.radius
        w = self.weight
        s = self._stroke
        f = self._fill
        if w: pygame.draw.circle(srf, s, (x,y), r)
        if f or w:
            if not f: f = 255, 255, 255, 0
            pygame.draw.circle(srf, f, (x,y), r - w)
        return srf
    
    def containsPoint(self, pos):
        return dist(pos, self.plotPos) <= self.r

    def contains(self, pos):
        cv = self.canvas
        if cv: pos = cv.relXY(pos)
        return dist(pos, self.pos) <= self.radius


class PLocus(Locus, Plotable):

    def __init__(self, data, param, **kwargs):
        self.data = data
        self.param = list(param)
        if len(param) < 3: self.param.append(100)
        self.vars = kwargs

    def draw(self, srf, snapshot=False):
        if snapshot: x0, y0 = 0, 0
        else: x0, y0 = self.canvas.rect.topleft
        px = getattr(self.plot, "pix", None)
        d = self.data
        pts = d if type(d) in (list, tuple) else locus(d, self.param, **self.vars)
        if px: pts = (px(*p) for p in pts)
        pts = [(x + x0, y + y0) for (x, y) in pts]
        if len(pts) > 1:
            wt = self.weight
            return pygame.draw.lines(srf, self.stroke, False, pts, wt).inflate(wt, wt)
        else: return pygame.Rect(0,0,0,0)


class PVector(Plotable, Renderable):
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

    def rotate(self, angle, xy=None):
        if xy is None: xy = self.plotPos
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
        u = PVector(1, u.dir if isinstance(u, PVector) else u)
        return (u * (self * u)).config(_plot=self._plot)

    def components(self, **kwargs):
        x = self.proj(0).config(tail=self.tail, **kwargs)
        y = self.proj(90).config(tip=self.tip, **kwargs)
        return [x, y]

    def __add__(self, other):
        xy = sigma(self.xy, other.xy)
        return PVector(xy=xy).config(_plot=self._plot)

    def __sub__(self, other):
        return self + other * -1

    def __mul__(self, other):
        if isinstance(other, PVector):
            x1, y1 = self.xy
            x2, y2 = other.xy
            return x1 * x2 + y1 * y2
        else:
            return PVector(other * self.mag, self.dir).config(_plot=self._plot)

    def __truediv__(self, x):
        return PVector(self.mag / x, self.dir).config(_plot=self._plot)

    def shift(self, dx=0, dy=0):
        tx, ty = self.tail
        self.tail = tx + dx, ty + dy

    @property
    def plotPos(self):
        tx, ty = self.tail
        x, y = self.xy
        return tx + x/2, ty + y/2

    @plotPos.setter
    def plotPos(self, xy):
        cx, cy = self.plotPos
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
