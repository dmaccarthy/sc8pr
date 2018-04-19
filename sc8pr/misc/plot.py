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


def _lrbt(lrbt, w, h):
    "Calculate coordinate system limits"
    n = len(lrbt)
    if n < 4:
        dy = h * (lrbt[1] - lrbt[0]) / w
        if n == 2:
            dy /= 2
            lrbt = lrbt + [-dy, dy]
        else: lrbt = lrbt + [lrbt[2] + dy]
    else: lrbt = lrbt[:4]
    return lrbt

def coordTr(lrbt, size):
    "Create a transformation for the given coordinate system"
    l, r = lrbt[:2]
    sx = size[0] / (r - l)
    dx = sx * l
    b, t = lrbt[2:]
    sy = size[1] / (b - t)
    dy = sy * t
    return lambda p: (sx * p[0] - dx, sy * p[1] - dy)

def locus(func, param, **kwargs):
    "Generate a parameterized sequence of 2D points"
    print(param)
    t0, t1, steps = param
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
    _stroke = rgba((0, 0, 0))
    weight = 0
    marker = None

    @property
    def stroke(self): return self._stroke

    @stroke.setter
    def stroke(self, s): self._stroke = rgba(s) if s else None

    def __init__(self, x, y=None, param=None, **kwargs):
        self._data = x if y is None else list(zip(x, y))
        self.param = param
        self.vars = kwargs

    def __getitem__(self, i): return self._data[i]
    def __setitem__(self, i, v): self._data[i] = v

    config = Graphic.config

    def pointGen(self):
        "Iterable sequence of points"
        data = self._data
        return data if type(data) in (list, tuple) else locus(data, self.param, **self.vars)

    @property
    def pointList(self):
        "Return data as a new list"
        return list(self.pointGen())

    def data(self, n):
        "Generate values from x or y column of data table"
        for pt in self.pointGen(): yield pt[n]

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
        pts = [transform(p) for p in self.pointGen()]
        s, w = self.stroke, self.weight
        if s and w: pygame.draw.lines(srf, rgba(s), False, pts, w)

        # Plot markers
        marker = self.marker
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
    def _tick(param, marker=9, y=False, **kwargs):
#        if marker is None: marker = 9
        if type(marker) is int: marker = ((9,1) if y else (1,9), "black")
        label = type(marker) is str
        if not (label or isinstance(marker, Graphic)):
            marker = Image(*marker)
        s = list(Series.lattice(0, param) if y else Series.lattice(param, 0))
        if label:
            isZero = (lambda x: _isZero(x, marker)) if kwargs.get("omitZero")\
                else (lambda x: False)
            i = 1 if y else 0
            text = list(marker.format(x[i]) for x in s)
            marker = [Text("" if isZero(x) else x).config(**kwargs)
                for x in text]
        return Series(s).config(marker=marker)

    def scaleMarkers(self, s):
        marker = self.marker
        if isinstance(marker, Graphic): marker = [marker]
        if marker:
            for gr in marker:
                gr.height *= s


class Plot(Renderable):
    "Class for plotting multiple data series with lines and markers"
    bg = None
    _xaxis = None
    _yaxis = None
    contains = Image.contains

    def __init__(self, size, lrbt):
        self._size = size
        self.coords = _lrbt(lrbt, *size)
        self._keys = []
        self._series = {}

    @property
    def size(self): return self._size

    @size.setter
    def size(self, size): self.resize(size)

    def resize(self, size):
        s = size[1] / self._size[1]
        for k in self: self[k].scaleMarkers(s)
        super().resize(size)

    @property
    def coords(self): return self._coords

    @coords.setter
    def coords(self, lrbt):
        self._coords = _lrbt(lrbt, *self._size)
        self.stale = True

    def __len__(self): return len(self._keys)

    def __setitem__(self, k, s):
        if type(k) is int: raise TypeError("Key cannot be an integer")
        if k in self._keys: self._keys.remove(k)
        self._series[k] = s
        self._keys.append(k)
        self.stale = True

    def __delitem__(self, k):
        if type(k) is int: k = self._keys[k]
        del self._series[k]
        self._keys.remove(k)
        self.stale = True

    def __getitem__(self, k):
        if type(k) is int: k = self._keys[k]
        return self._series[k]

    def __iter__(self):
        "Generate the Series keys"
        for k in self._keys: yield k

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

    @staticmethod
    def labels(text, pos, **kwargs):
        "Create a Series of Text labels"
        text = [Text(t).config(**kwargs) for t in text]
        return Series(pos, marker=text)

    @staticmethod
    def xtick(param, marker=9, **kwargs):
        return Series._tick(param, marker, **kwargs)

    @staticmethod
    def ytick(param, marker=9, **kwargs):
        return Series._tick(param, marker, True, **kwargs)

    def _drawAxis(self, srf, n, transform, x, stroke, weight):
        "Draw the axes onto the plot surface"
        x0, x1 = x
        x0, x1 = [(0,x0), (0,x1)] if n else [(x0,0), (x1,0)]
        pygame.draw.line(srf, stroke, transform(x0), transform(x1), weight)

    def render(self):
        "Render the plot as a surface"
        srf = Image(self._size, self.bg).image
        transform = coordTr(self._coords, self._size)
        if self._xaxis: self._drawAxis(srf, 0, transform, *self._xaxis)
        if self._yaxis: self._drawAxis(srf, 1, transform, *self._yaxis)
        for k in self._keys: self._series[k].draw(srf, transform)
        return srf

    def pixelCoords(self, xy):
        return coordTr(self._coords, self._size)(xy)


class PlotSprite(Plot, BaseSprite): pass


class Locus(Shape):
    "Class for drawing point sequences directly to the canvas"
    snapshot = None

    def __init__(self, data, lrbt, param, **kwargs):
        self.data = data
        self.lrbt = lrbt
        self.param = param
        self.kwargs = kwargs

    def _getCoordTr(self):
        sz = self.canvas.size
        return coordTr(_lrbt(self.lrbt, *sz), sz) 

    def contains(self, pos): return False

    @property
    def size(self):
        return self.rect.size if hasattr(self, "rect") else (0,0)

    def draw(self, srf, snapshot=False):
        "Draw the locus to the sketch or canvas snapshot"
        if snapshot: x0, y0 = 0, 0
        else: x0, y0 = self.canvas.rect.topleft
        tr = self._getCoordTr()
        d = self.data
        pts = d if type(d) in (list, tuple) else locus(d, self.param, **self.kwargs)
        pts = [tr(p) for p in pts]
        pts = [(x + x0, y + y0) for (x, y) in pts]
        return pygame.draw.lines(srf, self.stroke, False, pts, self.weight)

    def pointGen(self):
        "Generate a sequence of points using canvas pixel coordinates"
        d = self.data
        pts = d if type(d) in (list, tuple) else locus(d, self.param, **self.kwargs)
        tr = self._getCoordTr()
        for p in pts: yield tr(p)

    @property
    def pointList(self):
        return list(self.pointGen())
