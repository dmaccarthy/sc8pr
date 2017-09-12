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


from random import random
from math import hypot, ceil, atan2
import pygame
from sc8pr import Graphic, BaseSprite
from sc8pr.util import rgba, hasAny
from sc8pr.geom import transform2dGen, DEG, dist, delta


class Shape(Graphic):
    _fill = None
    _stroke = rgba((0, 0, 0))
    weight = 1

    @property
    def stroke(self): return self._stroke

    @stroke.setter
    def stroke(self, s): self._stroke = rgba(s) if s else None

    @property
    def fill(self): return self._fill

    @fill.setter
    def fill(self, s): self._fill = rgba(s) if s else None

    def contains(self, pos):
        "Determine if the point is within the circle, accounting for canvas offset"
        cv = self.canvas
        cvPos = delta(pos, cv.rect.topleft) if cv else pos
        return self.containsPoint(cvPos)


class Circle(Shape):
    radius = None
    shape = None
    
    def __init__(self, r):
        self.radius = r
        self._srf = None

    @property
    def size(self):
        d = ceil(2 * self.radius)
        return d, d

    def resize(self, size):
        self.radius = min(size) / 2
        self._srf = None

    def config(self, **kwargs):
        keys = "fill", "stroke", "weight", "radius"
        if hasAny(kwargs, keys): self._srf = None
        return super().config(**kwargs)

    @property
    def image(self):
        if self._srf: return self._srf
        srf = pygame.Surface(self.size, pygame.SRCALPHA)
        r = round(self.radius)
        w = self.weight
        if w: pygame.draw.circle(srf, self._stroke, (r,r), r)
        f = self._fill
        if f or w:
            if not f: f = 0, 0, 0, 0
            pygame.draw.circle(srf, f, (r,r), r-w)
        self._srf = srf
        return srf

    def containsPoint(self, pos):
        "Determine if the point is within the circle; do not account for canvas offset"
        return dist(self.pos, pos) < self.radius


class Line(Shape):
    resolution = 1e-10
    snapshot = None

    def __init__(self, start, point=None, vector=None):
        "Create a line or line segment"
        self.pos = start
        if point:
            ux = point[0] - start[0]
            uy = point[1] - start[1]
        elif type(vector) in (int, float):
            ux = 1
            uy = vector
        else: ux, uy = vector
        self._size = abs(ux), abs(uy)
        self.length = u = hypot(ux, uy)
        self.u = ux / u, uy / u

    def point(self, s=0):
        "Return the coordinates of a point on the line"
        px, py = self.pos
        ux, uy = self.u
        return px + s * ux, py + s * uy

    def midpoint(self):
        return self.point(self.length/2)

    def parameters(self, point):
        "Find parameters (s,d) of point q = p0 + s*u + d*n where n is perpendicular to u"
        pos = self.pos
        dx = point[0] - pos[0]
        dy = point[1] - pos[1]
        ux, uy = self.u
        return ux * dx + uy * dy, ux * dy - uy * dx
    
    def closest(self, point):
        "Find the point on the line / segment closest to the specified point"
        s = self.parameters(point)[0]
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
            p1 = self.pos
            p2 = other.pos
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            s1 = (u2x * dy - u2y * dx) / det
            if self.length is None or (s1 >= 0 and s1 <= self.length):
                s2 = (u1x * dy - u1y * dx) / det
                if other.length is None or (s2 >= 0 and s2 <= other.length):
                    return self.point(s1)
        else: # Lines are parallel
            s0, d = self.parameters(other.point())
            if d <= self.resolution:
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

# Drawing and canvas interaction

    def draw(self, srf, snapshot=False):
        cv = self.canvas
        dx, dy = (0, 0) if snapshot else cv.rect.topleft
        x1, y1 = self.point(0)
        x2, y2 = self.point(self.length)
        return pygame.draw.line(srf, self._stroke, (x1+dx,y1+dy),
            (x2+dx,y2+dy), max(1,round(self.weight)))

    def contains(self, pos):
        return abs(self.parameters(pos)[1]) <= 1 + self.weight / 2

    def resize(self, size):
        ux, uy = self.u
        dx, dy = size
        if ux < 0: dx = -dx
        if uy < 0: dy = -dy
        self.__init__(self.pos, vector=(dx,dy))


class Polygon(Shape):
    _angle = 0

    def __init__(self, pts, center=None):
        if center is None:
            w, h = self._calcRect(pts)[1]
            center = w/2, h/2
        self.pos = center
        self._points = [delta(pt, center) for pt in pts]
        self.dumpCache()

    @property
    def anchor(self): return None

    @property
    def angle(self): return self._angle
 
    @angle.setter
    def angle(self, a):
        da = a - self._angle
        self._angle = a
        self.transform(rotate=da)

    def dumpCache(self):
        self._srf = None
        self._size = None
        self._segCache = None

    def config(self, **kwargs):
        keys = "fill", "stroke", "weight"
        if hasAny(kwargs, keys): self._srf = None
        return super().config(**kwargs)

    def pointsGen(self):
        x, y = self.pos
        for p in self._points: yield p[0] + x, p[1] + y

    @property
    def points(self): return list(self.pointsGen())

    @staticmethod
    def _calcRect(pts):
        left = right = top = bottom = None
        for (x,y) in pts:
            if left is None or x < left: left = x
            if right is None or x > right: right = x
            if top is None or y < top: top = y
            if bottom is None or y > bottom: bottom = y
        return (left, top), (right - left, bottom - top)

    @property
    def size(self):
        if self._size is None:
            self._corner, self._size = self._calcRect(self._points)
        return self._size

    def blitPosition(self, offset, blitSize):
        "Return the position (top left) to which the graphic is drawn"
        x, y = self.pos
        dx, dy = self._corner
        p = self.weight
        return x + offset[0] + dx - p/2, y + offset[1] + dy - p/2

    def transform(self, scale=1, rotate=0):
        self._points = list(transform2dGen(self._points, scale=scale, rotate=rotate))
        self.dumpCache()

    def resize(self, size):
        "Resize the polygon (e.g. when scaling the canvas)"
        w, h = self.size
        f = size[0] / w, size[1] / h
        self.transform(scale=f)
        return f

    @property
    def image(self):
        if self._srf is None:
            p = self.weight
            w, h = self.size
            w = max(1, ceil(w) + p)
            h = max(1, ceil(h) + p)
            srf = pygame.Surface((w,h), pygame.SRCALPHA)
#            srf.fill((255,0,0,96))
            d = self._corner[0] - p/2, self._corner[1] - p/2
            pts = [delta(pt, d) for pt in self._points]
            w, f, s = round(self.weight), self._fill, self._stroke
            if f: pygame.draw.polygon(srf, f, pts)
            if w and s: pygame.draw.polygon(srf, s, pts, w)
#             x, y = delta((p/2,p/2), self._corner)
#             pygame.draw.circle(srf, (0,0,0), (round(x), round(y)), 2)
            self._srf = srf
        return self._srf

    def _segments(self):
        "Generate the line segments of the polygon"
        pts = self.points
        p1 = pts[-1]
        for i in range(len(pts)):
            p2 = pts[i]
            yield Line(p1, p2)
            p1 = p2

    @ property
    def segments(self):
        if not self._segCache:
            self._segCache = tuple(self._segments())
        return self._segCache

    def containsPoint(self, pos):
        "Determine if the point is within the circle; do not account for canvas offset"
        w, h = self.size
        x, y = self.pos
        l = Line(pos, (x + w + random(), y + h))
        n = 0
        for s in self._segments():
            if s.intersect(l): n += 1
        return n % 2 == 1


class Arrow(Polygon):

    def __init__(self, tail, length, angle=0, width=None, head=None, flatness=1):
        if type(length) not in (int, float):
            dx = length[0] - tail[0]
            dy = length[1] - tail[1]
            length = hypot(dx, dy)
            angle = atan2(dy, dx) / DEG
        if width is None: width = length / 10
        if head is None: head = width
        y = flatness * head
        x = length - head
        w = width / 2
        pts = (0, -w), (x, -w), (x, -y), (length, 0), (x, y), (x, w), (0, w)
        pts = tuple(transform2dGen(pts, rotate=angle, shift=tail))
        super().__init__(pts)


class PolygonSprite(Polygon, BaseSprite):

    def resize(self, size):
        f = Polygon.resize(self, size)
        self.scaleVectors(*f, attr=("vel", "acc"))


class ArrowSprite(Arrow, BaseSprite):
    resize = PolygonSprite.resize
