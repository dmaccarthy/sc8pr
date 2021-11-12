# Copyright 2015-2021 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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


def _lrbt(lrbt, w, h):
    "Calculate coordinate system limits"
    lrbt = list(lrbt)
    n = len(lrbt)
    if n < 4:
        dy = (h - 1) * (lrbt[1] - lrbt[0]) / (w - 1)
        if n == 2:
            dy /= 2
            lrbt = lrbt + [-dy, dy]
        else: lrbt = lrbt + [lrbt[2] + dy]
    else: lrbt = lrbt[:4]
    return lrbt

def _makeCS(lrbt, size, margin=0):
    "Create transformations between pixels and a coordinate system"
    w, h = size
    ml, mr, mb, mt = 4 * [margin] if type(margin) in (int, float) else margin
    w -= ml + mr
    h -= mb + mt
    lrbt = _lrbt(lrbt, w, h)
    l, r, b, t = lrbt
    sx = (w - 1) / (r - l)
    sy = (h - 1) / (b - t)
    dx = sx * l - ml
    dy = sy * t - mt
    cs = lambda p: ((p[0] + dx) / sx, (p[1] + dy) / sy)
    px = lambda p: (sx * p[0] - dx, sy * p[1] - dy)
    return cs, px
