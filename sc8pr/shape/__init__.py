# Copyright 2015-2021 D.G. MacCarthy <http://dmaccarthy.github.io>
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
from math import hypot, ceil
import pygame
from sc8pr import Graphic, Canvas, BaseSprite, CENTER, Image
from sc8pr.util import rgba, hasAny
from sc8pr.geom import transform2dGen, dist, delta, polar2d, circle_intersect, DEG, sigma


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


class Circle(Shape):
    xy = 0, 0
    quickDraw = False

    def __init__(self, r): self.r = r

    def __str__(self):
        return "<{}: r={:.3g}, xy=({:.3g}, {:.3g})>".format(self._str_name, self._r, *self.xy)

    @property
    def pos(self):
        xy = self.xy
        try: return self.canvas.px(*xy)
        except: return xy

    @pos.setter
    def pos(self, pos):
        try: self.xy = self.canvas.cs(*pos)
        except: self.xy = pos

    @property
    def anchor(self): return CENTER

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

    def contains(self, pos):
        return abs(self.parameters(pos)[1]) <= 1 + self.weight / 2

    def resize(self, size):
        ux, uy = self.u
        dx, dy = size
        if ux < 0: dx = -dx
        if uy < 0: dy = -dy
        self.__init__(self._start, vector=(dx,dy))


class Polygon(Shape):
    _angle = 0

    def setPoints(self, pts, anchor=None):
        self._dumpCache()
        self.vertices = v = []
        p0 = None
        for p in pts:
            if p != p0: v.append(p)
            p0 = p
        self._metrics()
        self.anchor = anchor

    __init__ = setPoints

    @staticmethod
    def _findRect(pts):
        return tuple((min(x[i] for x in pts), max(x[i] for x in pts)) for i in (0,1))

    def _metrics(self):
        
        # Metrics in canvas coordinates
        if not self.canvas: self.canvas = Canvas((10, 10))
        cv = self.canvas
        v = self.vertices
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
        if type(a) is int: self._anchor = self.vertices[a]
        elif a: self._anchor = a
        else: self._anchor = self._csrect["center"]

    @property
    def xy(self): return self._anchor

    @xy.setter
    def xy(self, xy):
        d = delta(xy, self._anchor)
        pts = (sigma(v, d) for v in self.vertices)
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
        pts = self.vertices
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
        pts = transform2dGen(self.vertices, shift=shift, preShift=True, rotate=rotate, scale=scale)
        return self.setPoints(list(pts), self._anchor)

    def resize(self, size):
        "Resize the polygon (e.g. when scaling the canvas)"
        w, h = self._rect.size
        f = size[0] / w, size[1] / h
        self.transform(scale=f)
        return f


TIP = 0
MIDDLE = None
TAIL = True

class Arrow(Polygon):
    "Arrow shaped graphic"

    def __init__(self, length, width=0.1, head=0.1, flatness=2, anchor=TIP):
        if anchor == TAIL: anchor = (-length, 0)
        width *= length / 2
        head *= length
        y = head * flatness / 2
        pts = [(0,0), (-head, y), (-head, width), (-length, width),
            (-length, -width), (-head, -width), (-head, -y)]
        super().__init__(pts, anchor)
        self.xy = 0, 0

    @staticmethod
    def between(tail, tip, width=0.1, head=0.1, flatness=2):
        r, a = polar2d(*delta(tip, tail))
        return Arrow(r, width, head, flatness, TIP).config(xy=tip, angle=a)


class ArrowSprite(Arrow, BaseSprite):

    @staticmethod
    def between(tail, tip, width=0.1, head=0.1, flatness=2):
        r, a = polar2d(*delta(tip, tail))
        return ArrowSprite(r, width, head, flatness, TIP).config(xy=tip, angle=a)


class CircleSprite(Circle, BaseSprite): pass
class PolygonSprite(Polygon, BaseSprite): pass


# !!!! Re-write for canvas coordinates!


class Ellipse(Shape):
    anchor = CENTER

    def resize(self, size):
        self._size = size
        self._srf = None

    __init__ = resize

    def config(self, **kwargs):
        keys = "fill", "stroke", "weight", "size", "arc"
        if hasAny(kwargs, keys): self._srf = None
        return super().config(**kwargs)

    @property
    def image(self):
        if self._srf: return self._srf
        srf = pygame.Surface(self._size, pygame.SRCALPHA)
        w = self.weight
        f = self._fill
        r = (0, 0), self._size
        if w:
            if isinstance(self, Arc):
                a = [-x * DEG for x in self.arc]
                pygame.draw.arc(srf, self._stroke, r, a[1], a[0], w)
            else:
                pygame.draw.ellipse(srf, self._stroke, r)
        if f:
            r = w / 2, w / 2, self.width - w, self.height - w
            if not f: f = 0, 0, 0, 0
            pygame.draw.ellipse(srf, f, r)
        if self.angle:
            srf = pygame.transform.rotate(srf, -self.angle)
        self._srf = srf
        return srf

    def containsPoint(self, pos):
        a, b = [x/2 for x in self.size]
        x, y = self.relXY(pos)
        return ((x - a) / a) ** 2 + ((y - b) / b) ** 2 <= 1


class Arc(Ellipse):
    arc = 0, 360

    @property
    def fill(self): return None

    @fill.setter
    def fill(self, f): raise NotImplementedError("Arc class does not support fill operation")

    def __init__(self, size):
        if type(size) in (int, float): size = size, size
        super().__init__(size)

    contains = Image.contains
