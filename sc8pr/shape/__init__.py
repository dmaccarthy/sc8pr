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


from random import random
from math import hypot, ceil, sin, cos, pi, atan
from sys import stderr
import pygame
from sc8pr import Graphic, Canvas, BaseSprite, CENTER, Image
from sc8pr.util import rgba, hasAny, logError
from sc8pr.geom import transform_gen, transform2d, dist, delta, polar2d, circle_intersect, DEG, sigma, neg


class Shape(Graphic):
    _fill = None
    _stroke = rgba((0, 0, 0))
    weight = 1

    @property
    def scrollable(self): return False

    @property
    def stroke(self): return self._stroke

    @stroke.setter
    def stroke(self, s): self._stroke = rgba(s) if s else None

    @property
    def fill(self): return self._fill

    @fill.setter
    def fill(self, s): self._fill = rgba(s) if s else None

    @property
    def avgColor(self):
        f = self._fill
        return f if f else self._stroke

    def contains(self, pos):
        "Determine if the point is within the shape, accounting for canvas offset"
        cv = self.canvas
        if cv: pos = cv.cs(*delta(pos, cv.rect.topleft))
        return self.containsPoint(pos)


class _Ellipse(Shape):
    xy = 0, 0

    @property
    def anchor(self): return CENTER

    @property
    def pos(self):
        xy = self.xy
        try: return self.canvas.px(*xy)
        except: return xy

    @pos.setter
    def pos(self, pos):
        try: self.xy = self.canvas.cs(*pos)
        except: self.xy = pos


class Circle(_Ellipse):
    quickDraw = True
    _preserve = "xy", "r"

    def __init__(self, r): self.r = r

    def __str__(self):
        return "<{}: r={:.3g}, xy=({:.3g}, {:.3g})>".format(self._str_name, self._r, *self.xy)

    @property
    def r(self): return self._r

    @r.setter
    def r(self, r):
        self._r = r
        self._srf = None

    @property
    def radius(self):
        "Radius in pixels"
        try: u = self.canvas.unit
        except: u = 1
        return u * self._r

    @radius.setter
    def radius(self, radius):
        try: u = self.canvas.unit
        except: u = 1
        self.r = radius / u

    @property
    def size(self):
        d = ceil(2 * self.radius)
        return d, d

    def resize(self, size):
        self.radius = min(size) / 2

    def config(self, **kwargs):
        keys = "fill", "stroke", "weight"
        if hasAny(kwargs, keys): self._srf = None
        return super().config(**kwargs)

    def containsPoint(self, xy):
        "Determine if the point is within the circle"
        return dist(self.xy, xy) < self.r

    def contains(self, pos):
        "Determine if the sketch position is within the blit radius"
        cv = self.canvas
        pos = delta(pos, cv.rect.topleft)
        return dist(self.pos, pos) < self.r * cv.unit

    def intersect(self, other):
        "Find the intersection(s) of two circles as list of points"
        return circle_intersect(self.xy, self.r, other.xy, other.r)

    @property
    def image(self):
        "Create a surface and draw the circle onto it"
        if self._srf: return self._srf
        srf = pygame.Surface(self.size, pygame.SRCALPHA)
        r = round(self.radius)
        pos = r, r
        wt = self.weight
        f = self._fill
        s = self._stroke
        if self.quickDraw: # Faster
            if f: pygame.draw.circle(srf, f, pos, r)
            if s and wt: pygame.draw.circle(srf, s, pos, r, wt)
        else: # Higher quality
            if wt: pygame.draw.circle(srf, s, pos, r)
            if f or wt:
                if not f: f = 0, 0, 0, 0
                pygame.draw.circle(srf, f, pos, r-wt)
        self._srf = srf
        return srf


class Line(Shape):
    resolution = 1e-10
    snapshot = None
    _preserve = "xy", "length"

    @property
    def xy(self): return self._start

    @xy.setter
    def xy(self, xy): self._start = xy

    @property
    def pos(self):
        xy = self._start
        try: return self.canvas.px(*xy)
        except: return xy

    @pos.setter
    def pos(self, pos):
        try: self.xy = self.canvas.cs(*pos)
        except: self.xy = pos

    def __init__(self, start, point=None, vector=None):
        "Create a line or line segment"
        self._start = start
        if point:
            ux = point[0] - start[0]
            uy = point[1] - start[1]
        elif type(vector) in (int, float):
            ux = 1
            uy = vector
        else: ux, uy = vector
        self._size = abs(ux), abs(uy)
        u = hypot(ux, uy)
        self.length = u #if point else None
        self.u = (ux / u, uy / u) if u else (0, 0)

    def __repr__(self):
        if self.length is None: p = "vector={}".format(self.u)
        else: p = "{}".format(self.point(self.length))
        return "{}({}, {})".format(type(self).__name__, self._start, p)

    def __str__(self):
        if self.length is None: p = "vector={}".format(self.u)
        else: p = "{}".format(self.point(self.length))
        return "<{}: {}, {}>".format(self._str_name, self._start, p)

    def point(self, s=0):
        "Return the coordinates of a point on the line"
        px, py = self._start
        ux, uy = self.u
        if s is True: s = self.length
        return px + s * ux, py + s * uy

    def midpoint(self):
        return self.point(self.length/2)

    def parameters(self, pt):
        "Find parameters (s,d) of point q = p0 + s*u + d*n where n is perpendicular to u"
        pos = self._start
        dx = pt[0] - pos[0]
        dy = pt[1] - pos[1]
        ux, uy = self.u
        return ux * dx + uy * dy, ux * dy - uy * dx
    
    def closest(self, pt):
        "Find the point on the line / segment closest to the specified point"
        s = self.parameters(pt)[0]
        l = self.length
        if l:
            if s < 0: s = 0
            elif s > l: s = l
        return self.point(s)

    def intersect(self, other):
        "Find the intersection of two lines / segments"
        u1x, u1y = self.u
        u2x, u2y = other.u
        det = u2x * u1y - u1x * u2y
        if det:
            p1 = self._start
            p2 = other._start
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            s1 = (u2x * dy - u2y * dx) / det
            if self.length is None or (s1 >= 0 and s1 <= self.length):
                s2 = (u1x * dy - u1y * dx) / det
                if other.length is None or (s2 >= 0 and s2 <= other.length):
                    return self.point(s1)
        else: # Lines are parallel
            s0, d = self.parameters(other.point())
            if abs(d) <= self.resolution:
                if self.length is None:  # self is a line
                    return True if other.length is None else other.midpoint()
                if other.length is None: # other is a line
                    return self.midpoint()
                # Both are segments
                s1 = self.parameters(other.point(other.length))[0]
                s0, s1 = min(s0, s1), max(s0, s1)
                s0 = max(0, s0)
                s1 = min(self.length, s1)
                if s1 >= s0: return self.point((s0 + s1) / 2)

    @property
    def normal(self):
        ux, uy = self.u
        return -uy, ux

# Drawing and canvas interaction

    def draw(self, srf, snapshot=False):
        if self.length is None:
            raise AttributeError("Unable to draw line; segment length is undefined")
        cv = self.canvas
        dx, dy = (0, 0) if snapshot else cv.rect.topleft
        x1, y1 = cv.px(*self.point())
        x2, y2 = cv.px(*self.point(True))
        wt = max(1, round(self.weight))
        r = pygame.draw.line(srf, self._stroke, (x1+dx,y1+dy), (x2+dx,y2+dy), wt)
        return r.inflate(wt, wt)

    def containsPoint(self, xy):
        "Check if a point is exactly on the line"
        return dist(self.closest(xy), xy) == 0

    def contains(self, pos):
        "Determine if the sketch position is 'near' the line"
        cv = self.canvas
        xy = cv.cs(*delta(pos, cv.rect.topleft))
        d = cv.px_delta(*delta(self.closest(xy), xy))
        return ceil(2 * hypot(*d)) <= max(2, self.weight)

    def resize(self, size):
        ux, uy = self.u
        dx, dy = size
        if ux < 0: dx = -dx
        if uy < 0: dy = -dy
        self.__init__(self._start, vector=(dx,dy))


class Polygon(Shape):
    _angle = 0
    _preserve = "anchor", "vertices"

    def setPoints(self, pts, anchor=None):
        self.vertices = pts
        self.anchor = anchor

    __init__ = setPoints

    @property
    def vertices(self): return self._vertices
    
    @vertices.setter
    def vertices(self, pts):
        self._dumpCache()
        self._vertices = v = []
        p0 = None
        for p in pts:
            if p != p0: v.append(p)
            p0 = p
        self._metrics()

    @staticmethod
    def _findRect(pts):
        return tuple((min(x[i] for x in pts), max(x[i] for x in pts)) for i in (0,1))

    def _metrics(self):
    
        # Metrics in canvas coordinates
        if not self.canvas: self.canvas = Canvas((10, 10))
        cv = self.canvas
        v = self._vertices
        (x0, x1), (y0, y1) = self._findRect(v)
        c = (x0 + x1) / 2, (y0 + y1) / 2
        self._csrect = dict(
            topleft = (x0, y0),
            size = (x1 - x0, y1 - y0),
            center = c)

        # Metrics in pixel coordinates
        self._px_vert = pts = cv.px_list(*v)
        (x0, x1), (y0, y1) = self._findRect(pts)
        w, h = abs(x1 - x0), abs(y1 - y0)
        wt = self.weight
        pos = round(x0) - wt, round(y0) - wt
        wt *= 2
        size = ceil(w) + wt, ceil(h) + wt
        self._rect = pygame.Rect(pos, size)

    def setCanvas(self, cv, key=None):
        super()._setCanvas(cv, key)
        self._metrics()

    def config(self, **kwargs):
        keys = "fill", "stroke", "weight"
        if hasAny(kwargs, keys): self._dumpCache()
        return super().config(**kwargs)

    def _dumpCache(self):
        self._srf = None
        self._segCache = None

    @property
    def image(self):
        "Return the most recent rendered Surface"
        if self._srf is None:
            wt, f, s = round(self.weight), self._fill, self._stroke
            offset = self._rect.topleft
            rnd = lambda x: (round(x[0]), round(x[1]))
            pts = [rnd(delta(p, offset)) for p in self._px_vert]
            self._srf = srf = pygame.Surface(self._rect.size, pygame.SRCALPHA)
            if f: pygame.draw.polygon(srf, f, pts)
            if wt and s: pygame.draw.polygon(srf, s, pts, wt)
        return self._srf

    @property
    def anchor(self): return self._anchor

    @anchor.setter
    def anchor(self, a):
        if type(a) is int: self._anchor = self._vertices[a]
        elif a: self._anchor = a
        else: self._anchor = self._csrect["center"]

    @property
    def xy(self): return self._anchor

    @xy.setter
    def xy(self, xy):
        d = delta(xy, self._anchor)
        pts = (sigma(v, d) for v in self._vertices)
        self.setPoints(pts)
        self._anchor = xy

    @property
    def pos(self):
        return self.canvas.px(*self._anchor)

    @pos.setter
    def pos(self, pos):
        self.xy = self.canvas.cs(*pos)

    @property
    def size(self): return self._rect.size

    @property
    def center(self): return self._rect.center

    def blitPosition(self, offset, blitSize):
        offset = delta(offset, self.canvas._scroll)
        return sigma(offset, self._rect.topleft)

    @property
    def angle(self): return self._angle

    @angle.setter
    def angle(self, a):
        self.transform(a - self._angle)
        self._angle = a

    def _segments(self):
        "Generate the line segments of the polygon"
        pts = self._vertices
        p1 = pts[-1]
        for i in range(len(pts)):
            p2 = pts[i]
            yield Line(p1, p2)
            p1 = p2

    @ property
    def segments(self):
        "Return a list of line segments that make up the polygon"
        if not self._segCache: self._segCache = list(self._segments())
        return self._segCache

    def intersect(self, other):
        "Find intersection(s) of polygon with another polygon or line; return a list of points"
        pts = []
        if isinstance(other, Polygon): other = other.segments
        else: other = other,
        for s in self.segments:
            for so in other:
                pt = s.intersect(so)
                if pt: pts.append(pt)
        return pts

    def containsPoint(self, xy):
        "Determine if the point is within the polygon; do not account for canvas offset"
        p = delta(self._csrect["topleft"], self._csrect["size"])
        l = Line(xy, p)
        n = 0
        for s in self._segments():
            if s.intersect(l): n += 1
        return n % 2 == 1

    def transform(self, rotate=0, scale=1):
        "Rotate and scale the Polygon around its anchor point"
        shift = self._anchor
        pts = list(transform_gen(self._vertices, True, scale, rotate, 1, self._anchor))
        return self.setPoints(pts, self._anchor)

    def resize(self, size):
        "Resize the polygon (e.g. when scaling the canvas)"
        w, h = self._rect.size
        f = size[0] / w, size[1] / h
        self.transform(scale=f)
        return f


TIP = 0
MIDDLE = None
TAIL = True
SHARP = 1
SIMPLE = 2

class Arrow(Polygon):
    "Arrow shaped polygon"

    def __init__(self, **kwargs):
        anchor = kwargs.get("anchor", TIP)
        tail = kwargs.get("tail", None)
        tip = kwargs.get("tip", None)
        if tail is None:
            if tip is None: tail = (0, 0)
            else:
                length, a = kwargs["length"], 0
                tail = (tip[0] - length, tip[1])                
        if tip is None:
            length, a = kwargs["length"], 0
            tip = (tail[0] + length, tail[1])
        else:
            length, a = polar2d(*delta(tip, tail))
        T = kwargs.get("width", 1/14)
        H = kwargs.get("head", 2/7)
        A = kwargs.get("angle", None)
        if A is None:
            f = kwargs.get("flatness", None)
            if f is None: A = 35
            else:
                A = atan(f/2) / pi * 180
                print("WARNING: 'flatness' option is deprecated; use 'angle'", file=stderr)
        shape = kwargs.get("shape", 0)
        if kwargs.get("relative", True):
            T *= length
            H *= length
        pts = Arrow._vert(length, T, H, A, shape)
        super().__init__(pts, TIP)
        self.config(xy=tip, angle=a)
        if anchor == TAIL: self.config(anchor=tail)
        elif anchor == MIDDLE: self.config(anchor=self.middle)

    @property
    def tip(self): return self.vertices[0]

    @property
    def tail(self):
        v = self.vertices
        n = len(v) // 2
        v, u = v[n:n+2]
        return (v[0] + u[0]) / 2, (v[1] + u[1]) / 2

    @property
    def middle(self):
        v = self.vertices[0]
        u = self.tail
        return (v[0] + u[0]) / 2, (v[1] + u[1]) / 2

    @staticmethod
    def _vert(L, T=None, H=None, A=35, shape=0): # www.desmos.com/calculator/kr61ws62tm
        if T is None: T = L / 14
        if H is None: H = 4 * T
        A *= pi / 180
        c = cos(A)
        s = sin(A)
        T2 = T / 2;
        x1 = -H * c
        x2 = x1 - T * s
        y1 = H * s
        y2 = y1 - T * c
        x3 = x2 - (T2 - y2) * c / s
        if x3 < x2 or shape == 2: x3 = x2
        if y2 < T2: y2 = T2
        pts = [(0,0), (x1, y1), (x2, y2), (x3, T2), (-L, T2),
            (-L, -T2), (x3, -T2), (x2, -y2), (x1, -y1)]
        if (shape or y1 < T2):
            del pts[8]
            del pts[1]
        return pts


class Ellipse(_Ellipse):
    _angle = 0
    _preserve = "xy", "axes"

    def __init__(self, axes): self.axes = axes

    @property
    def axes(self): return self._cssize

    @axes.setter
    def axes(self, size):
        self._cssize = (size, size) if type(size) in (int, float) else size
        self._srf = None

    @property
    def angle(self): return self._angle

    @angle.setter
    def angle(self, a):
        self._srf = None
        self._angle = a

    def resize(self, size):
        w, h = self.size
        fx, fy = size[0] / w, size[1] / h
        w, h = self._cssize
        self.axes = fx * w, fy * h

    @property
    def size(self):
        try:
            w, h = self.canvas.px_delta(*self._cssize)
            return ceil(abs(w)), ceil(abs(h))
        except:
            return self._cssize

    @size.setter
    def size(self, size): self.resize(size)

    def config(self, **kwargs):
        keys = "fill", "stroke", "weight", "angle"
        if hasAny(kwargs, keys): self._srf = None
        return super().config(**kwargs)

    @property
    def image(self):
        if self._srf: return self._srf
        srf = pygame.Surface(self.size, pygame.SRCALPHA)
        r = pygame.Rect((0, 0), self.size)
        self._render(srf, r)
        if self.angle:
            srf = pygame.transform.rotate(srf, -self.angle)
        self._srf = srf
        return srf
    
    def _render(self, srf, r):
        w = self.weight
        f = self._fill
        s = self._stroke
        if s and w:
            pygame.draw.ellipse(srf, s, r)
            d = -2 * w
            r.inflate_ip(d, d)
            tp = not f
            if tp: f = pygame.Color((255, 255, 255, 255) if s[0] < 128 else (0, 0, 0, 255))
        else: tp = False
        if f:
            pygame.draw.ellipse(srf, f, r)
            if tp: 
                pygame.PixelArray(srf).replace(f, (255,255,255,0))
        return srf

    def containsPoint(self, xy):
        a = -1 if self.clockwise else 1
        w, h = self._cssize
        x, y = transform2d(xy, shift1=neg(self.xy), matrix=a*self.angle)
        return (x / w) ** 2 + (y / h) ** 2 <= 0.25


class Arc(Ellipse):
    contains = Image.contains
    arc = 0, 360

    def _render(self, srf, r):
        w = self.weight
        s = self._stroke
        if s and w:
            a = -1 if self.clockwise else 1
            arc = [a*x * DEG for x in self.arc]
            if a == -1: pygame.draw.arc(srf, s, r, arc[1], arc[0], w)
            else: pygame.draw.arc(srf, s, r, arc[0], arc[1], w)


class CircleSprite(Circle, BaseSprite): pass
class EllipseSprite(Ellipse, BaseSprite): pass
class ArcSprite(Arc, BaseSprite): pass
class PolygonSprite(Polygon, BaseSprite): pass
class ArrowSprite(Arrow, BaseSprite): pass
