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

# from math import sin, cos
import pygame
from pygame.math import Vector2
from sc8pr import Canvas, Graphic, Renderable, CENTER
from sc8pr.shape import Line, Arrow, Shape
from sc8pr.geom import transform2d
from sc8pr.misc.plot import locus
from sc8pr.plot import _PObject


class PLocus(Shape):
    _scrollAdjust = False
    snapshot = None

    def __init__(self, data, param=None, **kwargs):
        self.data = data
        if param is not None:
            self.param = list(param)
            if len(param) < 3: self.param.append(100)
        self.vars = kwargs

    def contains(self, pos): return False

    @property
    def size(self):
        return self.rect.size if hasattr(self, "rect") else (0,0)

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


class PVector(_PObject, Renderable, Vector2):
    "Represent and draw 2D vectors"
    tail = 0, 0
    stroke = "red"
    weight = 3
    arrowShape = 16, 10
    contains = Graphic.contains

    def __init__(self, mag=None, theta=0, xy=(0,0)):
        if isinstance(mag, Vector2):
            xy = mag
            if isinstance(mag, PVector): self.tail = mag.tail
            mag = None
        super().__init__(xy)
        if mag is not None:
            if mag < 0:
                mag = -mag
                theta += 180
            self.from_polar((mag, theta))

    def __str__(self):
        r, t = self.as_polar()
        return "<{} {:.3g} @ {:.1f} ({:.3g}, {:.3g})>".format(type(self).__name__, r, t, *self)

    @property
    def anchor(self): return CENTER

    @property
    def csPos(self):
        "Midpoint of tail and tip"
        return tuple(Vector2(self.tail) + self / 2)

    @csPos.setter
    def csPos(self, xy):
        self.tail = tuple(Vector2(xy) - self / 2)

    @property
    def tip(self):
        return tuple(Vector2(self.tail) + self)

    @tip.setter
    def tip(self, xy):
        self.tail = tuple(Vector2(xy) - self)

    @property
    def mag(self): return self.length()

    @mag.setter
    def mag(self, r): self.scale_to_length(r)

    @property
    def theta(self): return self.as_polar()[1]

    @theta.setter
    def theta(self, t): self.from_polar((self.length(), t))

    def rotate(self, angle, xy=None):
        "Rotate around an arbitrary point"
        if xy is None: xy = self.csPos
        self.tail = transform2d(self.tail, rotate=angle, shift=xy, preShift=True)
        self.rotate_ip(angle)

    def proj(self, u):
        "Return projection onto a vector or direction"
        if not isinstance(u, PVector): u = PVector(1, u)
        else: u.normalize_ip()
        return (u * (u * self)).config(tail=self.tail)

    def components(self, **kwargs):
        "Return x and y components as a list"
        x = self.proj(0).config(**kwargs)
        y = self.proj(90).config(tip=self.tip, **kwargs)
        return [x, y]

    @staticmethod
    def sum(args):
        s = Vector2()
        for v in args: s += v
        return PVector(xy=s)

    def __add__(self, other):
        return PVector(xy=Vector2.__add__(self, other))

    def __sub__(self, other):
        return PVector(xy=Vector2.__sub__(self, other))

    def __mul__(self, other):
        v = Vector2.__mul__(self, other)
        return PVector(xy=v) if isinstance(v, Vector2) else v

    def __rmul__(self, other):
        v = Vector2.__rmul__(self, other)
        return PVector(xy=v) if isinstance(v, Vector2) else v

    def __truediv__(self, x):
        return PVector(xy=Vector2.__truediv__(self, x))

    def render(self):
        "Render the vector as an arrow on a pygame.Surface"
        l = self.length() * self.canvas.unit
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
