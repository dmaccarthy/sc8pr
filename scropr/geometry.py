# Copyright 2015-2016 D.G. MacCarthy <http://dmaccarthy.github.io>
#
# This file is part of "scropr".
#
# "scropr" is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "scropr" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "scropr".  If not, see <http://www.gnu.org/licenses/>.


from math import pi, sin, cos, acos, degrees, radians, atan
from math import hypot

def tuple_add(*args):
    return tuple([sum([args[i][j] for i in range(len(args))]) for j in range(len(args[0]))])

def tuple_avg(*args):
    n = len(args)
    return tuple_times(tuple_add(*args), 1 / n) if n else None

def tuple_neg(t):
    return tuple([-x for x in t])

def tuple_sub(t1, t2):
    return tuple_add(t1, tuple_neg(t2))

def tuple_times(t, s):
    return tuple([s*x for x in t])

def distance(p1, p2):
    "Calculate the distance between two points"
    x1, y1 = p1
    x2, y2 = p2
    return hypot(x2 - x1, y2 - y1)

def polar(pt, deg=False):
    "Convert a point from (x,y) to (r,a) form"
    x, y = pt
    r = hypot(x, y)
    if r == 0: return r, 0
    a = acos(x/r)
    if y < 0: a = 2 * pi - a
    return r, degrees(a) if deg else a

def opposite_angle(a, degrees=False):
    opp = 180 if degrees else pi
    return a + (-opp if a >= opp else opp)

def transform(pts, **kwargs):
    "Generator to perform a transformation on a sequence of points"
    if "matrix" in kwargs: m = kwargs["matrix"]
    else:
        if "rotate" in kwargs:
            a = kwargs["rotate"]
            if "degrees" in kwargs:
                if kwargs["degrees"]: a = radians(a)
            c, s = cos(a), sin(a)
            m = c, -s, s, c
        else:
            m = 1, 0, 0, 1
        if "scale" in kwargs:
            s = kwargs["scale"]
            m = [s*a for a in m]
    sx, sy = kwargs["shift"] if "shift" in kwargs else (0, 0)
    for x, y in pts:
        yield x * m[0] + y * m[1] + sx, x * m[2] + y * m[3] + sy

def arrowPolar(length, angle=0, tail=None, tailWidth=None, headLength=None, flatness=1, degrees=True):
    "Return a sequence of vertices for an arrow shape"
    if tailWidth == None: tailWidth = length / 10
    if headLength == None: headLength = 1.5 * tailWidth
    x = length - headLength
    y0 = tailWidth / 2
    y1 = headLength * flatness / (3 ** 0.5)
    if y1 < y0: y1 = y0
    if x < length / 4: x = length / 4
    pts = (0,y0), (x,y0), (x,y1), (length,0), (x,-y1), (x,-y0), (0,-y0)
    if angle or tail:
        if tail == None: tail = 0, 0
        pts = tuple(transform(pts, rotate=angle, shift=tail, degrees=degrees))
    return pts

def arrow(tail, tip, tailWidth=None, headLength=None, flatness=1):
    "Return a sequence of vertices for an arrow shape"
    r = polar((tip[0] - tail[0], tip[1] - tail[1]))
    return arrowPolar(r[0], r[1], tail, tailWidth, headLength, flatness, degrees=False)

def locus(func, t0, t1, steps, **params):
    "Generate a parameterized sequence of points"
    for i in range(steps + 1):     
        try: yield func(t0 + i * (t1 - t0) / steps, **params)
        except: pass 

def _between(x1, x2, x):
    "Test if x is between x1 and x2 inclusive"
    return x >= x1 and x <= x2 or x >= x2 and x <= x1

def between(p1, p2, p):
    "Test if p is in or on the rectangle defined by p1 and p2"
    return _between(p1[0], p2[0], p[0]) and _between(p1[1], p2[1], p[1])

def eqnOfLine(p1, p2):
    "Return coefficients for equation ax + by + c = 0"
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2:
        if y1 == y2:
            raise ValueError("Two distinct points are required")
        return 1, 0, -x1
    m = (y2-y1) / (x2-x1)
    return m, -1, y1 - m * x1

def linearEval(coeff, x=None, y=None):
    "Evaluate x or y from a linear equation"
    a, b, c = coeff
    if x is None:
        return None if a==0 or y is None else -(b * y + c) / a
    else:
        return None if b==0 else -(a * x + c) / b

def closest(coeff, pt):
    "Find the closest point on a line to the specified point"
    a, b, c = coeff
    x, y = pt
    d = a * y - b * x
    if a == 0: return -d/b, -c/b
    if b == 0: return -c/a, d/a
    y = (a*d - b*c) / (a*a + b*b)
    return (a*y - d)/b, y

def pointSegment(p1, p2, pt):
    "Calculate the distance from a point p to the line segment p1-p2"
    p = closest(eqnOfLine(p1, p2), pt)
    if between(p1, p2, p):
        return distance(pt, p), p
    else:
        r1, r2 = distance(pt, p1), distance(pt, p2)
        return (r1, p1) if r1 < r2 else (r2, p2)

def unitVector(p1, p2=None):
    "Return a unit vector pointing from p1 to p2"
    if p2 is None:
        p1, p2 = (0,0), p1
    r = distance(p1, p2)
    if r == 0: return 0, 0
    x1, y1 = p1
    x2, y2 = p2
    return (x2 - x1) / r, (y2 - y1) / r

def scalarProduct(v1, v2): 
    "Return the scalar product of two vectors"
    return sum([v1[i] * v2[i] for i in range(len(v1))])

def direction_of_line(eqn, perp=False):
    a, b = eqn[:2]
    if a and b:
        if perp: a = -1 / a
        return atan(a)
    else:
        vert = (perp and a == 0) or (not perp and b == 0)
        return pi / 2 if vert else 0

# Intersections...

def intersect(c1, c2):
    "Find the intersection of two lines"
    a1, b1, c1 = c1
    a2, b2, c2 = c2
    if a1 == a2 and b1 == b2: # Parallel
        return False #c1 == c2
    yd = a1 * b2 - a2 * b1
    if yd:
        y = (a2 * c1 - a1 * c2) / yd
        x = (b1 * y + c1) / (-a1) if a1 else (b2 * y + c2) / (-a2)
    else:
        x = (b2 * c1 - b1 * c2) / (b1 * a2 - b2 * a1)
        y = (a1 * x + c1) / (-b1) if b1 else (a1 * x + c1) / (-b1)
    return x, y

def intersect_segments(s1, s2, c1=None, c2=None):
    "Find the intersection of two line segments"
    if c1 is None: c1 = eqnOfLine(*s1)
    if c2 is None: c2 = eqnOfLine(*s2)
    p = intersect(c1, c2)
    if p is False: return False
    return p if withinSegment(*s1, p=p) and withinSegment(*s2, p=p) else False

def withinSegment(p1, p2, p):
    "Is a point that is on the line within the segment?"
    p1x, p1y = p1
    p2x, p2y = p2
    px, py = p
    a1 = polar((px-p1x, py-p1y), True)[1]
    a2 = polar((px-p2x, py-p2y), True)[1]
    return abs(a1 - a2) > 179

def intersect_line_circle(coeff, center, r):
    "Find the intersections of a line and circle"
    xy = closest(coeff, center)
    s = distance(center, xy)
    if s == r: return xy,
    elif s < r:
        a, b = coeff[:2]
        if b:
            dx, dy = unitVector((0,0), (b,-a))
            s = (r**2 - s**2) ** 0.5
            dx *= s
            dy *= s
        else:
            dx, dy = 0, 1
        x, y = xy
        return (x + dx, y + dy), (x - dx, y - dy)
    return ()

def intersect_segment_circle(seg, center, r, coeff=None):
    "Find the intersection of a line segment and a circle"
    if coeff is None: coeff = eqnOfLine(*seg)
    pts = [p for p in intersect_line_circle(coeff, center, r) if between(*seg, p=p)]
    return pts

def _segments(pts, closed=True):
    "Generate a sequence of line segments from points"
    n = 0
    prev = None
    for pt in pts:
        if n: yield prev, pt
        else: pt0 = pt
        prev = pt
        n += 1
    if closed: yield pt, pt0

def segments(pts, closed=True):
    return tuple(_segments(pts, closed))

def _polygon_eqn(poly):
    "Determine the equations of the sides of a polygon"
    for i in range(len(poly)):
        seg = poly[i-1:i+1] if i else (poly[-1], poly[0])
        yield eqnOfLine(*seg)

def intersect_polygon(p1, p2, findAll=False):
    "Find the intersections of two polygons"
    c1 = tuple(_polygon_eqn(p1))
    c2 = tuple(_polygon_eqn(p2))
    pts = set()
    for i in range(len(p1)):
        s1 = p1[i-1:i+1] if i else (p1[-1], p1[0])
        for j in range(len(p2)):
            s2 = p2[j-1:j+1] if j else (p2[-1], p2[0])
            pt = intersect_segments(s1, s2, c1[i], c2[j])
            if pt:
                if findAll: pts.add(pt)
                else: return True
    return pts if findAll else False
