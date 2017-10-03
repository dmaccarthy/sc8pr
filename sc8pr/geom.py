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


from math import hypot, pi, sin, cos, atan2, floor

DEG = pi / 180

def positiveAngle(a):
    "Return an angle between 0 and 360"
    return a - 360 * floor(a / 360)

def angleDifference(a2, a1=0):
    "Difference between 2 directions; [-180,180)"
    return positiveAngle(a2 - a1 + 180) - 180

def dist(p1, p2):
    "Distance between two points"
    return hypot(p2[0] - p1[0], p2[1] - p1[1])

def sprod(v1, v2):
    "2D scalar product"
    return v1[0] * v2[0] + v1[1] * v2[1]

def delta(vf, vi=None, mag=None):
    "vf - vi, rescaled to specified magnitude"
    if vi:
        x = vf[0] - vi[0]
        y = vf[1] - vi[1]
    else: x, y = vf
    if mag:
        r = hypot(x, y)
        if r:
            mag /= r
            x *= mag
            y *= mag
    return x, y

def vec2d(r, a, deg=True):
    "2D Polar to Cartesian conversion"
    if deg: a *= DEG
    return r * cos(a), r * sin(a)

def polar2d(vx, vy, deg=True):
    "2D Cartesian to Polar conversion"
    a = atan2(vy, vx)
    return hypot(vx, vy), (a / DEG if deg else a)

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
