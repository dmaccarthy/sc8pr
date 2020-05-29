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


from math import hypot, pi, sin, cos, asin, atan2, floor, sqrt

DEG = pi / 180

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

def sprod(v1, v2):
    "2D scalar product"
    return v1[0] * v2[0] + v1[1] * v2[1]

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

def _matrix(rotate=0, scale=1, rev=False):
    "Create a 2x2 matrix (as a 4-tuple) to perform a scale transformation and a rotation"
    sx, sy = (scale, scale) if type(scale) in (float, int) else scale
    if rotate:
        rotate *= DEG
        c, s = cos(rotate), sin(rotate)
    else: c, s = 1, 0
    if rev: # Rotate before scaling
        return sx * c, -sx * s, sy * s, sy * c
    else:   # Scale before rotating
        return sx * c, -sy * s, sx * s, sy * c

def transform2dGen(pts, mx=None, shift=(0,0), preShift=None, **kwargs):
    "Generator to perform a linear transformation and shift on a sequence of points"
    xa, ya = shift
    if preShift is True: xb, yb = -xa, -ya
    elif preShift: xb, yb = preShift
    m0, m1, m2, m3 = mx if mx else _matrix(**kwargs)
    for (x,y) in pts:
        if preShift:
            x += xb
            y += yb
        x, y = m0 * x + m1 * y, m2 * x + m3 * y
        yield (x + xa, y + ya)

def transform2d(pt, **kwargs):
    "Perform a linear transformation and shift on a single point"
    return tuple(transform2dGen((pt,), **kwargs))[0]

def rotatedSize(w, h, angle):
    pts = (w,h), (w,-h), (-w,h), (-w,-h)
    pts = list(transform2dGen(pts, rotate=angle))
    w = max(abs(pt[0]) for pt in pts)
    h = max(abs(pt[1]) for pt in pts)
    return w, h

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
