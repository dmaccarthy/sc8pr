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

import pygame

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


class CoordSys:
    "Representation of a coordinate system associated with a Canvas"

    def __init__(self, lrbt, size, margin=0):
        self._args = lrbt, margin, size
        w, h = size
        ml, mr, mb, mt = 4 * [margin] if type(margin) is int else margin
        w -= ml + mr
        h -= mb + mt
        self.viewport = pygame.Rect(ml, mt, w, h)
        l, r, b, t = lrbt = _lrbt(lrbt, w, h)
        self.lrbt = tuple(lrbt)
        sx = (w - 1) / (r - l)
        sy = (h - 1) / (b - t)
        dx = sx * l - ml
        dy = sy * t - mt
        cs = lambda p: ((p[0] + dx) / sx, (p[1] + dy) / sy)
        px = lambda p: (sx * p[0] - dx, sy * p[1] - dy)
        self._tr = cs, px

    @staticmethod
    def calcSize(lrbt, margin, scale):
        if type(margin) is int: margin = 4 * [margin]
        mx = sum(margin[:2]) + 1
        my = sum(margin[2:]) + 1
        l, r, b, t = lrbt
        try: sx, sy = scale
        except: sx, sy = scale, scale
        return round(abs((r - l) * sx) + mx), round(abs((t - b) * sy) + my)


def makeCS(lrbt, size, margin=0): return CoordSys(lrbt, size, margin)._tr
