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


from math import hypot, pi, sin, cos, asin, atan2, floor, sqrt

DEG = pi / 180

try: from math import prod
except:
    def prod(iterable, start=1):
        for x in iterable: start *= x
        return start

def positiveAngle(a):
    "Return an angle between 0 and 360"
    return a - 360 * floor(a / 360)

def smallAngle(a):
    "Return an angle between -180 and 180"
    return positiveAngle(a + 180) - 180

def angleDifference(a2, a1=0):
    "Difference between 2 directions; [-180,180)"
    return positiveAngle(a2 - a1 + 180) - 180

def dist(p1, p2):
    "Distance between two points"
    return hypot(p2[0] - p1[0], p2[1] - p1[1])

def sigma(*args):
    "Sum one or more vectors"
    return tuple(sum(x[i] for x in args) for i in range(len(args[0])))

def delta(v2, v1=None, mag=None):
    "v2 - v1, rescaled to specified magnitude"
    if v1:
        x = v2[0] - v1[0]
        y = v2[1] - v1[1]
    else: x, y = v2
    if mag is not None:
        r = hypot(x, y)
        if r:
            mag /= r
            x *= mag
            y *= mag
    return x, y

# 2D Vector multiplications
def neg(v): return -v[0], -v[1]
def smult(s, v):return s * v[0], s * v[1]
def sprod(v1, v2): return v1[0] * v2[0] + v1[1] * v2[1]
def vmult(v1, v2): return v1[0] * v2[0], v1[1] * v2[1]
def vprod(v1, v2): return v1[0] * v2[1] - v1[1] * v2[0]

def shiftAlongNormal(x, y, deriv, dr):
    m = deriv(x, y)
    if m == 0: dx, dy = 0, dr
    else:
        m = -1 / m
        dx = (-dr if m > 0 else dr) / sqrt(1 + m*m)
        dy = m * dx
    return x + dx, y + dy

def vec2d(r, a, deg=True):
    "2D Polar to Cartesian conversion"
    if deg: a *= DEG
    return r * cos(a), r * sin(a)

def polar2d(vx, vy, deg=True):
    "2D Cartesian to Polar conversion"
    a = atan2(vy, vx)
    return hypot(vx, vy), (a / DEG if deg else a)

def subtend(P, C, r, maxSep=None):
    "Position relative to P in polar form, and angle subtended by a circle C of radius r"
    sep, direct = polar2d(*delta(C, P))
    if maxSep is None or sep <= maxSep:
        half = 180.0 if sep < r else asin(r / sep) / DEG
        return sep, direct, half

def transform_gen(pts, shift1=None, scale1=1, matrix=(1,0,0,1), scale2=1, shift2=None):
    "Transform (rotate, scale, translate) a sequence of 2D points"
    isNum = lambda x: type(x) in (int, float)
    if shift2 is True: shift2 = neg(shift1)
    elif shift1 is True: shift1 = neg(shift2)
    if isNum(scale1): s1x = s1y = scale1
    else: s1x, s1y = scale1
    if isNum(scale2): s2x = s2y = scale2
    else: s2x, s2y = scale2
    if isNum(matrix):
        r = matrix * DEG
        c, s = cos(r), sin(r)
        matrix = c, -s, s, c
    m0, m1, m2, m3 = matrix
    m0 *= s2x * s1x
    m1 *= s2x * s1y
    m2 *= s2y * s1x
    m3 *= s2y * s1y
    cx, cy = shift1 if shift1 else (0, 0)
    sx, sy = shift2 if shift2 else (0, 0)
    for (x, y) in pts:
        x += cx
        y += cy
        yield m0 * x + m1 * y + sx, m2 * x + m3 * y + sy

def transform2d(pt, shift1=None, scale1=1, matrix=(1,0,0,1), scale2=1, shift2=None):
    "Perform a transformation on a single point"
    return next(transform_gen((pt,), shift1, scale1, matrix, scale2, shift2))

def rotatedSize(w, h, angle):
    pts = (w,h), (w,-h), (-w,h), (-w,-h)
    pts = list(transform_gen(pts, matrix=angle))
    return tuple(max(abs(pt[i]) for pt in pts) for i in (0, 1))

def circle_intersect(c1, r1, c2, r2):
    "Find the intersection(s) of two circles as list of points"
    d = dist(c1, c2)
    if d > r2 + r1 or d == 0 or d < abs(r2 - r1): return []
    r_sq = r2 * r2
    x = (d*d + r_sq - r1 * r1) / (2*d)
    ux, uy = delta(c1, c2, 1)
    x0, y0 = c2
    x0 += x * ux
    y0 += x * uy
    if x < r2:
        y = sqrt(r_sq - x*x)
        return [(x0 - y * uy, y0 + y * ux), (x0 + y * uy, y0 - y * ux)]
    else: return [(x0, y0)]
