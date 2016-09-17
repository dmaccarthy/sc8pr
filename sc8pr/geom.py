# Copyright 2015-2016 D.G. MacCarthy <http://dmaccarthy.github.io>
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

from math import pi, sin, cos, acos, degrees, radians, sqrt, hypot
from random import random

TWO_PI = 2 * pi
DEG = pi / 180
RAD = 180 / pi


# Tuple arithmetic...

def add(v1, v2): return tuple(x + y for x,y in zip(v1,v2))
def sub(v1, v2): return tuple(x - y for x,y in zip(v1,v2))
def sprod(v1, v2): return sum(x * y for x,y in zip(v1,v2))
def times(v, s): return tuple(x * s for x in v)
def neg(v): return tuple(-x for x in v)
def zero(dim=2): return tuple(0 for i in range(dim))
def dist(p1, p2): return mag(sub(p2, p1))
def distSq(p1, p2): return mag(sub(p2, p1), 2)

def mag(v, n=1):
    "Calculate |v| ** n"
    v = sprod(v, v)
    if n != 2: v = v ** (n/2)
    return v

def vsum(*args):
    "Sum an arbitrary number of tuples"
    v = args[0]
    for a in args[1:]: v = add(v, a)
    return v

def avg(*args):
    "Average an arbitrary number of tuples"
    return times(vsum(*args), 1/len(args))

def cross2d(v1, v2, i=2):
    "Cross product of 2D vectors; or one component of 3D cross product"
    x = (i + 1) % 3
    y = (i + 2) % 3
    return v1[x] * v2[y] - v1[y] * v2[x]

def cross3d(v1, v2):
    "Cross product of 3D vectors"
    return tuple(cross2d(v1, v2, i) for i in range(3))

def unitVector(v):
    "Resize the vector to unit length"
    m = mag(v)
    return times(v, 1/m) if m else None

def vec2d(r, a):
    "Create an (x,y) tuple from a magnitude and direction (in radians)"
    return r * cos(a), r * sin(a)

def normal2d(v):
    "Return a 2D vector rotated by +pi/2 radians"
    x, y = v
    return -y, x

def polar2d(v):
    "Return the magnitude and direction (in radians) as a 2-tuple"
    r = hypot(*v)
    if r:
        x, y = v
        a = acos(x/r)
        if y < 0: a = TWO_PI - a
    else: a = 0
    return r, a

def rad2d(v): return polar2d(v)[1]
def deg2d(v): return degrees(polar2d(v)[1])

def resolve2d(v, u):
    "Calculate parallel and perpendicular components"
    ux, uy = u
    return sprod(v, u), sprod(v, (-uy, ux))

def cosine(v1, v2):
    "Scalar product of unit vectors"
    sq = mag(v1, 2) * mag(v2, 2)
    return sprod(v1, v2) / sqrt(sq) if sq else None

def angleBetween(v1, v2):
    "Angle between two vectors in radians"
    a = cosine(v1, v2)
    return 0 if a is None else acos(a)

def transform(v, matrix):
    "Apply a transformation matrix to a vector"
    return tuple(sprod(v, row) for row in matrix)

def transform2dMatrix(rotate=0, scale=1):
    "Return a matrix for 2D rotations and scale transformations"
    c, s = vec2d(scale, rotate) if rotate else (scale, 0)
    return (c, -s), (s, c)

def transform2d(v, rotate=0, scale=1, shift=None):
    "Apply a 2D rotation and/or scale transformation"
    v = transform(v, transform2dMatrix(rotate, scale))
    return add(v, shift) if shift else v


class Line:
    "Represent a line in n-dimensions using a point and unit vector"

    def __init__(self, point1, point2, isPoint=True):
        self._point = point1
        v = sub(point2, point1) if isPoint else point2
        self._unit = unitVector(v)

    def __str__(self):
        return "<Line: {} + s * {}>".format(self._point, self._unit)
    
    @property
    def unit(self): return self._unit

    @property
    def line(self): return self

    def eval(self, s=None):
        "Return a point on the line given a parameter value"
        return add(self._point, times(self._unit, self.length if s is None else s))

    def solve(self, x, dim=0):
        "Return a point on the line given one of the coordinates"
        try:
            s = x - self._point[dim] / self._unit[dim]
            return self.eval(s)
        except: pass

    def param(self, point):
        "Find the parameter of the point on the line closest to the specified point"
        return sprod(self._unit, sub(point, self._point))

    def closest(self, point):
        "Point on the line closest to the specified point"
        return self.eval(self.param(point))

    def distance(self, point):
        "Distance from point to nearest point on the line"
        return dist(self.closest(point), point)

    def distSq(self, point):
        "Square of distance from point to nearest point on the line"
        return distSq(self.closest(point), point)

    def _intersect2d(self, other, parallel=0):
        ux, uy = self._unit
        vx, vy = other._unit
        d = vx * uy - ux * vy
        if d:
            dp = times(sub(other.eval(0), self.eval(0)), 1 / d)
            s = sprod(dp, (-vy, vx))
            t = sprod(dp, (-uy, ux))
            return s, t
        else:
            return self.line.distSq(other._point) <= parallel

    def intersect2d(self, other, parallel=0):
        "Intersection of 2D line with another 2D line or line segment"
        if isinstance(other, Segment):
            return other.intersect2d(self)
        i = self._intersect2d(other, parallel)
        return i if type(i) is bool else self.eval(i[0])

    @property
    def slope(self):
        "Slope of the line (2D only!)"
        x, y = self._unit
        if x: return y/x

    @property
    def normal(self):
        "Unit vector normal (+pi/4) to the line (2D only!)"
        return normal2d(self.unit)

    def coeff2d(self, standard=False):
        "Return slope and intercepts (m, y0, x0), or coefficients of ax + by + c=0"
        line = self.line
        m = line.slope
        y0 = line.solve(0)
        if y0 is not None: y0 = y0[1]
        x0 = line.solve(0, 1)
        if x0 is not None: x0 = x0[0]
        if standard:
            return (-1, 0, x0) if m is None else (m, -1, y0)
        else: return m, y0, x0


class Segment(Line):
    _lineClone = None

    def __init__(self, point1, point2):
        super().__init__(point1, point2)
        self.length = dist(point2, point1)

    @property
    def line(self): return super()

    def lineClone(self):
        if not self._lineClone:
            self._lineClone = Line(self._point, self.unit, False)
        return self._lineClone

    def paramOnSegment(self, s):
        return s >= 0 and s <= self.length

    def solve(self, x, dim=0):
        try:
            s = (x - self._point[dim]) / self._unit[dim]
            if self.paramOnSegment(s):
                return self.eval(s)
        except: pass

    def closest(self, point):
        "Point on the line segment closest to the specified point"
        s = self.param(point)
        l = self.length
        return self.eval(0 if s < 0 else l if s > l else s)

    def distanceSqFromEnd(self, point):
        return min(distSq(self.eval(0), point), distSq(self.eval(self.length), point))

    def intersect2d(self, other, parallel=0):
        "Intersection of 2D line segment with another 2D line segment"
        s = self._intersect2d(other, parallel)
        if s is True:
            lims = self.param(other.eval(0)), self.param(other.eval(other.length))
            low = max(min(lims), 0)
            high = min(max(lims), self.length)
            if low <= high:
                return [self.eval((low + high) / 2)]
        elif s:
            s, t = s
            if self.paramOnSegment(s):
                if not isinstance(other, Segment) or other.paramOnSegment(t):
                    return [self.eval(s)]
        return []


class Shape:

    def collide(self, other):
        "Determine if there is at least one intersection between two shapes"
        return len(self.intersect2d(other)) > 0 or self.contains(other) or other.contains(self)

    def contains(self, shape):
        if isinstance(shape, Circle2D): pt = shape.center
        elif isinstance(shape, Polygon2D): pt = shape.points[0]
        else: pt = shape
        return self.containsPoint(pt)


class Circle2D(Shape):

    def __init__(self, r=1, posn=(0,0)):
        self.radius = r
        self.center = posn

    def __str__(self):
        return "<Circle2D: r={} @ {}>".format(self.radius, self.center)

    @property
    def testPoint(self): return self.center

    @property
    def rSquared(self):
        r = self.radius
        return r * r

    def normal(self, point):
        "Inward pointing normal unit vector"
        return unitVector(sub(self.center, point))

    def closest(self, point):
        return sub(self.center, times(self.normal(point), self.radius))

    def containsPoint(self, point):
        return distSq(self.center, point) < self.rSquared

    def _circleIntersect(self, other):
        "Intersection of two circles"
        s2 = self.rSquared
        o2 = other.rSquared
        R2 = distSq(self.center, other.center)
        try:
            x = (R2 + s2 - o2) / (2 * sqrt(R2))
            line = Line(self.center, other.center)
            ux, uy = line.unit
            x2 = x * x
            return line.eval(x), None if x2 == s2 else times((-uy, ux), sqrt(s2 - x2))
        except: pass

    def intersect2d(self, other):
        "Return a tuple of intersection points with another circle or line/segment"
        if isinstance(other, Circle2D):
            s = self._circleIntersect(other)
            if s:
                pt, s = s
                return [pt] if s is None else [add(pt, s), sub(pt, s)]
        elif isinstance(other, Line):
            line = other.line
            pt = line.closest(self.center)
            x2 = distSq(self.center, pt)
            r2 = self.rSquared
            if x2 <= r2:
                if x2 == r2: pt = [pt]
                else:
                    s = times(line.unit, sqrt(r2 - x2))
                    pt = [add(pt, s), sub(pt, s)]
                if isinstance(other, Segment):
                    pt = [p for p in pt if other.paramOnSegment(other.param(p))]
                return pt
        else:
            return other.intersect2d(self)
        return []

    def transform2d(self, rotate=0, scale=1, shift=None):
        "Apply a 2D rotation and/or scale transformation"
        c = transform2d(self.center, rotate, scale, shift)
        return Circle2D(scale * self.radius, c)


class Polygon2D(Shape):
    
    def __init__(self, points):
        self.points = pts = points if type(points) is tuple else tuple(points)
        xmax = None
        for p in pts:
            x = p[0]
            if xmax is None or x > xmax: xmax = x
        self._segs = None
        self._outside = xmax + 50, random()

    @property
    def testPoint(self): return self.points[0]
    
    @property
    def segments(self):
        if self._segs is None:
            self._segs = tuple(self._segments())
        return self._segs

    def _segments(self):
        p0 = start = self.points[0]
        for p in self.points[1:]:
            yield Segment(p0, p)
            p0 = p
        yield Segment(p0, start)

    def _closest(self, point):
        r0 = None
        for seg in self.segments:
            pt = seg.closest(point)
            r1 = distSq(pt, point)
            if r0 is None or r1 < r0:
                r0 = r1
                data = pt, seg
        return data

    def closest(self, point): return self._closest(point)[0]

    def containsPoint(self, point):
        n = len(self.intersect2d(Segment(point, self._outside)))
        return n % 2 == 1

    def intersect2d(self, other):
        pts = []
        for seg in self.segments:
            pts.extend(other.intersect2d(seg))
        return pts

    def _transform2dGen(self, rotate=0, scale=1, shift=None):
        "Generator for 2D transformation"
        mx = transform2dMatrix(rotate, scale)
        for p in self.points:
            p = transform(p, mx)
            if shift: p = add(p, shift)
            yield p

    def transform2d(self, rotate=0, scale=1, shift=None):
        "Apply a 2D rotation, scale transformation and/or translation"
        return Polygon2D(self._transform2dGen(rotate, scale, shift))

# Other shapes...

def _ellipsygon(t, a, b, n):
    s, c = sin(t), cos(t)
    if c < 0: a = -a
    if s < 0: b = -b
    n = 1 / n
    x, y = a * abs(c) ** n, b * abs(s) ** n
    return x, y

def ellipsygon(a, b, n, v=16):
    dt = 2 * pi / v
    pts = [_ellipsygon(i * dt, a, b, n) for i in range(v)]
    return Polygon2D(pts)

def arrowPolar(length, angle=0, tail=None, tailWidth=None, headLength=None, flatness=1, degrees=True):
    "Return a sequence of vertices for an arrow shape"
    if tailWidth == None: tailWidth = length / 10
    if headLength == None: headLength = 1.5 * tailWidth
    x = length - headLength
    y0 = tailWidth / 2
    y1 = headLength * flatness / (3 ** 0.5)
    if y1 < y0: y1 = y0
    if x < length / 4: x = length / 4
    poly = Polygon2D([(0,y0), (x,y0), (x,y1), (length,0), (x,-y1), (x,-y0), (0,-y0)])
    if angle or tail:
        if degrees: angle = radians(angle)
        poly = poly.transform2d(rotate=angle, shift=tail)
    return poly

def arrow(tail, tip, tailWidth=None, headLength=None, flatness=1):
    "Return a sequence of vertices for an arrow shape"
    r, a = polar2d(sub(tip, tail))
    return arrowPolar(r, a, tail, tailWidth, headLength, flatness, degrees=False)

def locus(func, t0, t1, steps=None, **params):
    "Generate a parameterized sequence of points"
    if steps is None: steps = max(1, round(abs(t1-t0)))
    for i in range(steps + 1):     
        try: yield func(t0 + i * (t1 - t0) / steps, **params)
        except: pass


# Physics...

def impact(shape1, shape2):
    "Calculate the point and direction of impact for two colliding shapes"
    pts = shape1.intersect2d(shape2)
    n = len(pts)
    if n == 0: return None
    pt = avg(*pts)
    if isinstance(shape1, Circle2D): norm = shape1.normal(pt)
    elif isinstance(shape2, Circle2D): norm = neg(shape2.normal(pt))
    else:
        pt1, seg1 = shape1._closest(pt)
        pt2, seg2 = shape2._closest(pt)
        use1 = seg1.distanceSqFromEnd(pt1) >= seg2.distanceSqFromEnd(pt2)
        norm = seg1.normal if use1 else neg(seg2.normal)
    return pt, norm
