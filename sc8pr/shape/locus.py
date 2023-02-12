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

import pygame
from sc8pr.shape import Shape
from sc8pr.geom import sigma
from sc8pr import CENTER


def locus(func, param, **kwargs):
    "Generate a parameterized sequence of 2D points"
    t0, t1 = param[:2]
    steps = param[2] if len(param) > 2 else 100
    dt = (t1 - t0) / steps
    for i in range(steps + 1):     
        try:
            x = t0 + i * dt
            try: y = func(x, **kwargs)
            except: y = func(x)
            yield y if type(y) in (list, tuple) else (x, y)
        except: pass


class Locus(Shape):
    "Class for drawing point sequences directly to the canvas"
    
    autoPositionOnResize = False
    snapshot = None
    _preserve = ()

    @property
    def pos(self):
        return self.rect.center if hasattr(self, "rect") else (0,0)

    @property
    def anchor(self): return CENTER

    def __init__(self, data, param=None):
        self.data = data
        self.param = param
        self.coeff = {}

    def contains(self, pos): return False

    @property
    def size(self):
        return self.rect.size if hasattr(self, "rect") else (0,0)

    def draw(self, srf, snapshot=False):
        "Draw the locus to the sketch or canvas snapshot"
        if snapshot: x0, y0 = 0, 0
        else: x0, y0 = self.canvas.rect.topleft
        d = self.data
        pts = d if type(d) in (list, tuple) else locus(d, self.param, **self.coeff)
        cv = self.canvas
        pts = [sigma((x0, y0), cv.px(*p)) for p in pts]
        if len(pts) > 1:
            wt = self.weight
            return pygame.draw.lines(srf, self.stroke, False, pts, wt).inflate(wt, wt)
        else: return pygame.Rect(0,0,0,0)

    def pointGen(self):
        "Generate a sequence of points"
        d = self.data
        pts = d if type(d) in (list, tuple) else locus(d, self.param, **self.coeff)
        for p in pts: yield p

    @property
    def pointList(self):
        return list(self.pointGen())
