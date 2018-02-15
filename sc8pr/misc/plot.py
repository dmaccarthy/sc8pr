# Copyright 2015-2018 D.G. MacCarthy <http://dmaccarthy.github.io>
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
from sc8pr.util import rgba, rangef
from sc8pr.geom import rotatedSize, transform2dGen
from sc8pr.text import Text


def coordTr(lrbt, size):
    "Create a transformation for the given coordinate system"
    l, r = lrbt[:2]
    sx = size[0] / (r - l)
    dx = sx * l
    if len(lrbt) < 4: # Use same x and y scale
        sy = -abs(sx)
        if len(lrbt) == 3:
            t = lrbt[2]
            if t is True: # Axis in middle of plot
                t = (r - l) * size[1] / (2 * size[0])
        else: # Axis along bottom of plot
            t = (r - l) * size[1] / size[0]
    else:
        b, t = lrbt[2:]
        sy = size[1] / (b - t)
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

def leastSq(x, y):
    "Perform a simple least squares regression"
    n = len(x)
    if len(y) != n: raise ValueError("x and y data must be the same size")
    xav = sum(x) / n
    yav = sum(y) / n
    m = sum((x[i] - xav) * (y[i] - yav) for i in range(n))
    m /= sum((xi - xav) ** 2 for xi in x)
    b = yav - m * xav
    return (lambda x: m * x + b), (m, b)

def _isZero(x, fmt):
    "Check is text is formatted 0"
    fmt = fmt.format(0)
    return x == fmt or x == "-" + fmt


class Series:
    "Represents a single data series within the plot"

    def __init__(self, x, y=None, **kwargs):
        self._data = x if y is None else list(zip(x, y))
        self._opt = kwargs

    def __getitem__(self, i): return self._data[i]
    def __setitem__(self, i, v): self._data[i] = v

    def _dataPoints(self):
        "Iterable sequence of points"
        data = self._data
        return data if type(data) in (list, tuple) else locus(data, **self._opt) 

    @property
    def dataPoints(self):
        "Return data as a new list"
        return list(self._dataPoints())

    def data(self, n):
        for pt in self._dataPoints(): yield pt[n]

    @property
    def x(self): return list(self.data(0))

    @property
    def y(self): return list(self.data(1))

    def regression(self, model=leastSq):
        return model(*[list(self.data(i)) for i in (0, 1)])

    def transform(self, **kwargs):
        "Apply a transformation to the data points"
        try: self._data = list(transform2dGen(self._data, **kwargs))
        except: raise TypeError("Series.transform cannot be applied to an equation")
        return self

    def draw(self, srf, transform):
        "Plot one data series onto a surface"

        # Plot stroke
        options = self._opt
        pts = [transform(p) for p in self._dataPoints()]
        s, w = options.get("stroke"), options.get("weight")
        if s and w: pygame.draw.lines(srf, rgba(s), False, pts, w)
 
        # Plot markers
        marker = options.get("marker")
        if marker:
            i = 0
            for p in pts:
                if isinstance(marker, Graphic): img = marker
                else:
                    img = marker[i]
                    i += 1
                if img.canvas: img.remove()
                img.pos = p
                sz = img.size
                if img.angle: sz = rotatedSize(*sz, img.angle)
                pos = img.blitPosition((0,0), sz)
                srf.blit(img.image, pos)

    @staticmethod
    def lattice(x=0, y=0):
        "Generate a lattice of points"
        num = int, float
        x = (x,) if type(x) in num else rangef(*x)
        y = (y,) if type(y) in num else list(rangef(*y))
        for i in x:
            for j in y: yield i, j

    @staticmethod
    def xtick(x0, x1, dx, marker=None, y=False, **kwargs):
        if marker is None: marker = ((9,1) if y else (1,9), "black")
        label = type(marker) is str
        if not (label or isinstance(marker, Graphic)):
            marker = Image(*marker)
        s = list(Series.lattice(0, [x0, x1, dx]) if y
            else Series.lattice([x0, x1, dx], 0))
        if label:
            isZero = (lambda x: _isZero(x, marker)) if kwargs.get("omitZero")\
                else (lambda x: False)
            i = 1 if y else 0
            text = list(marker.format(x[i]) for x in s)
            marker = [Text("" if isZero(x) else x).config(**kwargs)
                for x in text]
        return Series(s, marker=marker)

    @staticmethod
    def ytick(x0, x1, dx, marker=None, **kwargs):
        return Series.xtick(x0, x1, dx, marker, True, **kwargs)


class Plot(Renderable):
    "Class for plotting multiple data series with lines and markers"
    bg = None
    _text = []
    _xaxis = None
    _yaxis = None

    def __init__(self, size, lrbt):
        self._size = size
        self.coords = lrbt
        self._keys = []
        self._series = {}

    @property
    def size(self): return self._size

    @size.setter
    def size(self, size): self.resize(size)

    @property
    def coords(self): return self._coords

    @coords.setter
    def coords(self, lrbt):
        self._coords = lrbt
        self.stale = True

    def __setitem__(self, k, v):
        if k in self._keys:
            self._keys.remove(k)
#            raise KeyError("Key '{}' is already in use".format(k))
        self._series[k] = v
        self._keys.append(k)
        self.stale = True

    def __delitem__(self, k):
        del self._series[k]
        self._keys.remove(k)
        self.stale = True

    def __getitem__(self, k):
        if type(k) is int: k = self._keys[i]
        return self._series[k]

    def axis(self, n=None, ends=None, stroke="black", weight=2):
        "Configure the x- and/or y-axis"
        if n is None:
            for n in range(2): self.axis(n, ends, stroke, weight)
        else:
            attr = ["_xaxis", "_yaxis"][n]
            if not ends: ends = self._coords[2:] if n else self._coords[:2]
            setattr(self, attr, (ends, rgba(stroke), weight))
        self.stale = True
        return self

    def drawAxis(self, srf, n, transform, x, stroke, weight):
        "Draw the axes onto the plot surface"
        x0, x1 = x
        x0, x1 = [(0,x0), (0,x1)] if n else [(x0,0), (x1,0)]
        pygame.draw.line(srf, stroke, transform(x0), transform(x1), weight)

#     def label(self, text, pos, **kwargs):
#         attr = {"marker":Text(text).config(**kwargs)}
#         self._text.append(([pos], attr))
#         self.stale = True
#         return self


    def render(self):
#         noDraw = not hasattr(self, "rect")
#         if noDraw: self.rect = pygame.Rect((0,0), self.size)
        srf = Image(self._size, self.bg).image
        transform = coordTr(self._coords, self._size)
        if self._xaxis: self.drawAxis(srf, 0, transform, *self._xaxis)
        if self._yaxis: self.drawAxis(srf, 1, transform, *self._yaxis)
        for k in self._keys:
            self._series[k].draw(srf, transform)
#         for d, k in (self._data + self._text):
#             self.plot(srf, d, transform, **k)
#         if noDraw: del self.rect
        return srf

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
