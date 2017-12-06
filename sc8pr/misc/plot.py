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


import pygame
from sc8pr import Renderable, Image, Graphic, BaseSprite
from sc8pr.shape import Shape
from sc8pr.util import rgba
from sc8pr.text import Text


def coordTr(lrbt, size):
    "Create a transformation for the given coordinate system"
    l, r, b, t = lrbt
    sx = size[0] / (r - l)
    sy = size[1] / (b - t)
    dx = sx * l
    dy = sy * t
    return lambda p: (sx * p[0] - dx, sy * p[1] - dy)

def locus(func, **kwargs):
    "Generate a parameterized sequence of 2D points"
    t0, t1, steps = kwargs["param"]
    for i in range(steps + 1):     
        try:
            x = t0 + i * (t1 - t0) / steps
            try: y = func(x, **kwargs)
            except: y = func(x)
            yield y if type(y) in (list, tuple) else (x, y)
        except: pass


class Plot(Renderable):
    "Class for plotting multiple data series with lines and markers"
    bg = None
    _coords = None
    _data = []
    _text = []

    def __init__(self, size, lrbt):
        self._size = size
        self.coords = lrbt

    @property
    def size(self): return self._size

    @size.setter
    def size(self, size): self.resize(size)

    @property
    def coords(self): return self._coords

    @coords.setter
    def coords(self, lrbt):
        assert len(lrbt) == 4
        self._coords = lrbt
        self.stale = True

    def series(self, data, **kwargs):
        self._data.append((data, kwargs))
        self.stale = True
        return self

    def label(self, text, pos, **kwargs):
        attr = {"marker":Text(text).config(**kwargs)}
        self._text.append(([pos], attr))
        self.stale = True
        return self

    def removeSeries(self, n):
        d = self._data
        d.remove(d[n])

    def render(self):
#         noDraw = not hasattr(self, "rect")
#         if noDraw: self.rect = pygame.Rect((0,0), self.size)
        srf = Image(self._size, self.bg).image
        transform = coordTr(self._coords, self._size)
        for d, k in (self._data + self._text):
            self.plot(srf, d, transform, **k)
#         if noDraw: del self.rect
        return srf

    def plot(self, srf, data, transform, **kwargs):
        "Plot one data series onto a surface"

        # Points
        pts = data if type(data) in (list, tuple) else locus(data, **kwargs)
        pts = [transform(p) for p in pts]
    
        # Plot stroke
        s, w = kwargs.get("stroke"), kwargs.get("weight")
        if s and w: pygame.draw.lines(srf, rgba(s), False, pts, w)

        # Plot markers
        marker = kwargs.get("marker")
        if marker:
            if not (isinstance(marker, Graphic) or isinstance(marker[0], Graphic)):
                color, radius = marker
                color = rgba(color)
                marker = None
            i = 0
            for p in pts:
                if marker:
                    if isinstance(marker, Graphic): img = marker
                    else:
                        img = marker[i]
                        i += 1
                    if img.canvas: img.remove()
                    img.pos = p
                    pos = img.blitPosition((0,0), img.size)
                    srf.blit(img.image, pos)
                else:
                    q = round(p[0]), round(p[1])
                    pygame.draw.circle(srf, color, q, radius)

    def resize(self, size):
        self._size = size
        self.stale = True

    contains = Image.contains

    def pixelCoords(self, xy):
        return coordTr(self._coords, self._size)(xy)


class PlotSprite(Plot, BaseSprite): pass


class Locus(Shape):
    "Class for drawing point sequences directly to the canvas"
    snapshot = None

    def __init__(self, data, lrbt, **kwargs):
        self.data = data
        self.lrbt = lrbt
        self.kwargs = kwargs

    def contains(self, pos): return False

    @property
    def size(self):
        return self.rect.size if hasattr(self, "rect") else (0,0)

    def draw(self, srf, snapshot=False):
        offset = 0, 0
        try:
            if not snapshot: offset = self.canvas.rect.topleft
        except: pass 
        s, w = self.stroke, self.weight
        transform = coordTr(self.lrbt, self.canvas.size)
        d = self.data
        pts = d if type(d) in (list, tuple) else locus(d, **self.kwargs)
        pts = [transform(p) for p in pts]
        if offset != (0, 0):
            pts = [(x + offset[0], y + offset[1]) for (x, y) in pts]
        return pygame.draw.lines(srf, s, False, pts, w)

    def pointGen(self, size=None):
        "Generate a sequence of points using canvas pixel coordinates"
        d = self.data
        pts = d if type(d) in (list, tuple) else locus(d, **self.kwargs)
        tr = coordTr(self.lrbt, self.canvas.size if size is None else size)
        for p in pts: yield tr(p)

    def pointList(self, size=None): return list(self.pointGen(size))
