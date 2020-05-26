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

import pygame
from sc8pr import Canvas, Image, Graphic, CENTER
from sc8pr.shape import Polygon

class Table(Canvas):

    def __init__(self, cols, rows, bg=None, padding=4):
        self._cols = tuple(cols)
        self._rows = tuple(rows)
        self._padding = padding
        p = 2 * padding
        size = sum(cols) + p, sum(rows) + p
        super().__init__(size, bg)

    @property
    def cols(self): return len(self._cols)

    @property
    def rows(self): return len(self._rows)

    def cell(self, c, r):
        cols = self._cols
        rows = self._rows
        if type(c) is int: c1 = c + 1
        else: c, c1 = c
        if type(r) is int: r1 = r + 1
        else: r, r1 = r
        p = self._padding
        xy = sum(cols[:c]) + p, sum(rows[:r]) + p
        return pygame.Rect(xy, (sum(cols[c:c1]), sum(rows[r:r1])))

    def box(self, c=None, r=None, **kwargs):
        if c is True:
            for c in range(self.cols):
                for r in range(self.rows):
                    self.box(c, r, **kwargs)
        else:
            if c is None: c = 0, self.cols
            if r is None: r = 0, self.rows
            rect = self.cell(c, r)
            pts = rect.topleft, rect.topright, rect.bottomright, rect.bottomleft
            self += Polygon(pts).config(**kwargs)
        return self

    @staticmethod
    def grid(*args, cols=None, size=None, fit=True):
        n = len(args)
        if cols is None: cols = n
        rows = (n - 1) // cols + 1
        args = [(a if isinstance(a, Graphic) else Image(a)) for a in args]
        w, h = size if size else args[0].size
        cv = Table(cols*[w], rows*[h])
        r = c = 0
        for a in args:
            cv += a.config(pos=cv.cell(c, r).center, anchor=CENTER)
            if fit:
                f = min(w/a.width, h/a.height)
                if f < 1: a.scale(f)
            c += 1
            if c == cols:
                c = 0
                r += 1
        return cv
