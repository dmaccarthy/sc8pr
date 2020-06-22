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

import pygame, re
from math import floor, ceil
from pygame.math import Vector2
from sc8pr import Canvas, Graphic, Image, Renderable, CENTER, BOTTOM, TOP
from sc8pr.shape import Line, Arrow, Shape
from sc8pr.geom import transform2d
from sc8pr.misc.plot import locus
from sc8pr.text import Text


class _PObject:
    autoPositionOnResize = _scrollAdjust = False
    theta = 0
    csPos = 0, 0

    @property
    def pos(self):
        cv = self.canvas
        return cv.px(*self.csPos) if cv else self.csPos

    @pos.setter
    def pos(self, pos):
        cv = self.canvas
        if cv: pos = cv.cs(*pos)
        self.csPos = pos

    @property
    def angle(self):
        cv = self.canvas
        return self.theta if cv is None or cv.clockwise else -self.theta

    @angle.setter
    def angle(self, a):
        cv = self.canvas
        self.theta = a if cv is None or cv.clockwise else -a

    def update(self, x, y): self.csPos = x, y

    def _warn(self): pass


class PBar(_PObject, Renderable):
    fill = "blue"
    stroke = "black"
    weight = 1
    contains = Graphic.contains

    @property
    def anchor(self):
        return BOTTOM if self._xy[1] >= 0 else TOP

    @property
    def csPos(self): return self._xy[0], 0

    @property
    def data(self): return self._xy

    @property
    def pos(self):
        x = self._xy[0]
        x1, y1 = self.canvas.px(x, 0)
        return x1, y1

    @pos.setter
    def pos(self, xy): pass

    @csPos.setter
    def csPos(self, xy): pass

    def __init__(self, x, y, barWidth=1):
        self._xy = x, y
        self._barWidth = barWidth

    def update(self, x, y):
        self.stale = True
        self._xy = x, y

    def render(self):
        y = self._xy[1]
        cv = self.canvas
        u = cv.units
        w = round(abs(u[0] * self._barWidth))
        h = round(abs(u[1] * y))
        wt = round(self.weight)
        img = Canvas((w, h + 1), self.fill).config(weight=wt, border=self.stroke)
        return img.snapshot().original


class PImage(_PObject, Image): pass
class PText(_PObject, Text): pass


class PLine(_PObject, Line):

    @property
    def csPos(self): return self._start

    @csPos.setter
    def csPos(self, pos): self._start = pos

    def contains(self, pos): return False
    def resize(self, size): pass

    def draw(self, srf, snapshot=False):
        if self.length is None:
            raise AttributeError("Unable to draw line; segment length is undefined")
        cv = self.canvas
        px = cv.px
        x1, y1 = px(*self.point())
        x2, y2 = px(*self.point(self.length))
        wt = max(1, round(self.weight))
        dx, dy = (0, 0) if snapshot else cv.rect.topleft
        r = pygame.draw.line(srf, self._stroke, (x1+dx,y1+dy), (x2+dx,y2+dy), wt)
        return r.inflate(wt, wt)


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

    def __repr__(self):
        r, t = self.as_polar()
        return "<{}({:.5g}, {:.5g})>".format(type(self).__name__, r, t)

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

    def __neg__(self):
        return PVector(xy=Vector2.__neg__(self))

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
        if l < 2:
            return Image((1, 1), self.stroke).image
        shape = self.arrowShape
        if type(shape) is dict:
            shape = shape.copy()
            if shape["fixed"]:
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

    @staticmethod
    def parse(string):
        "Parse a string as a list of PVector instances"
        expr = re.subn("\s*", "", string)[0]
        vecs = []
        while len(expr):
            neg = False
            if expr[0] in "+-":
                if expr[0] == "-": neg = True
                expr = expr[1:]
            n, v = _parse(expr, 0)
            if not n: n, v = _parse(expr, 1)
            if n:
                vecs.append(-1 * v if neg else v)
                expr = expr[n:]
            else: break
        if expr: raise ValueError("can't parse string '{}' as PVectors".format(string))
        return PVector.tipToTail(vecs)

    @staticmethod
    def tipToTail(vecs):
        "Adjust each vector's tail to match the previous vector's tip"
        if len(vecs) > 1:
            v0 = vecs[0]
            for v in vecs[1:]:
                v.tail = v0.tip
                v0 = v
        return vecs


# Regular expressions for Cartesian and polar form (whitespace removed)

_sign = "[-|\+]{0,1}"
_num = _sign + "\d+\.{0,1}\d*([e|E]" + _sign + "[\d]*){0,1}"
_re = [ # [Cartesian, Polar]
    re.compile("\(" + _num + "," + _num + "\)"),
    re.compile(_num + "@" + _num)
]

def _parse(expr, form):
    "Parse one vector"
    m = _re[form].match(expr)
    if m:
        m = m.group()
        n = len(m)
        if form:
            v = PVector(*[float(m.split("@")[i]) for i in (0, 1)])
        else:
            v = PVector(xy=[float(m[1:-1].split(",")[i]) for i in (0, 1)])
        return n, v
    return None, None
