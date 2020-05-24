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


from math import log, exp
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
        if not isinstance(lrbt, list): lrbt = list(lrbt)
        dy = h * (lrbt[1] - lrbt[0]) / w
        if n == 2:
            dy /= 2
            lrbt = lrbt + [-dy, dy]
        else: lrbt = lrbt + [lrbt[2] + dy]
    else: lrbt = lrbt[:4]
    return lrbt

def locus(func, param, **kwargs):
    "Generate a parameterized sequence of 2D points"
    t0, t1, steps = param
    dt = (t1 - t0) / steps
    for i in range(steps + 1):     
        try:
            x = t0 + i * dt
            try: y = func(x, **kwargs)
            except: y = func(x)
            yield y if type(y) in (list, tuple) else (x, y)
        except: pass

def leastSq(x, y):
    "Perform a simple least squares linear regression"
    n = len(x)
    if len(y) != n: raise ValueError("x and y data must be the same size")
    xav = sum(x) / n
    yav = sum(y) / n
    m = sum((x[i] - xav) * (y[i] - yav) for i in range(n))
    m /= sum((xi - xav) ** 2 for xi in x)
    b = yav - m * xav
    return (lambda x: m * x + b), (m, b)

def power(x, y):
    "Least squares fit to model y = a x**n"
    x = [log(xi) for xi in x]
    y = [log(xi) for xi in y]
    n, a = leastSq(x, y)[1]
    a = exp(a)
    return (lambda x:a * x**n), (a, n)

def expon(x, y):
    "Least squares fit to model y = a b**x"
    y = [log(xi) for xi in y]
    b, a = [exp(a) for a in leastSq(x, y)[1]]
    return (lambda x:a * b**x), (a, b)



### Functions and classes below are deprecated from v2.2

def coordTr(lrbt, size, invert=False):
    "Create a transformation for the given coordinate system"
    if len(lrbt) != 4: lrbt = _lrbt(lrbt, *size)
    l, r = lrbt[:2]
    sx = size[0] / (r - l)
    dx = sx * l
    b, t = lrbt[2:]
    sy = size[1] / (b - t)
    dy = sy * t
    if invert:
        return lambda p: ((p[0] + dx) / sx, (p[1] + dy) / sy)
    else:
        return lambda p: (sx * p[0] - dx, sy * p[1] - dy)

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

    def __init__(self, x, y=None, param=None):
        self._data = x if y is None else list(zip(x, y))
        self.param = param
        self.vars = {}

    def __getitem__(self, i): return self._data[i]
    def __setitem__(self, i, pt): self._data[i] = pt

    config = Graphic.config

    def pointGen(self):
        "Iterable sequence of points"
        data = self._data
        return data if type(data) in (list, tuple) else locus(data, self.param, **self.vars)

    @property
    def pointList(self):
        "Return data as a new list"
        return list(self.pointGen())

    def dataGen(self, n):
        "Generate values from x or y column of data table"
        for pt in self.pointGen(): yield pt[n]

    @property
    def x(self): return list(self.dataGen(0))

    @property
    def y(self): return list(self.dataGen(1))

    def regression(self, model=leastSq):
        return model(*[list(self.dataGen(i)) for i in (0, 1)])

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
    def _lattice(x=0, y=0):
        "Generate a lattice of points"
        num = int, float
        x = (x,) if type(x) in num else rangef(*x)
        y = (y,) if type(y) in num else list(rangef(*y))
        for i in x:
            for j in y: yield i, j

    @staticmethod
    def _tick(param, marker=9, y=False, **kwargs):
        if type(marker) is int: marker = ((9,1) if y else (1,9), "black")
        label = type(marker) is str
        if not (label or isinstance(marker, Graphic)):
            marker = Image(*marker)
        s = list(Series._lattice(0, param) if y else Series._lattice(param, 0))
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
    _xgrid = None
    _ygrid = None
#    contains = Image.contains

    def __init__(self, size, lrbt):
        self._size = size.size if hasattr(size, "size") else size
        self.coords = _lrbt(lrbt, *size)
        self._keys = []
        self._series = {}

    @property
    def clockwise(self):
        l, r, b, t = self._coords
        x = 1 if r > l else -1
        y = 1 if t > b else -1
        return x * y < 0

    @property
    def size(self): return self._size

    @size.setter
    def size(self, size): self.resize(size)

    def resize(self, size):
        s = size[1] / self._size[1]
        for k in self: self[k].scaleMarkers(s)
        super().resize(size)
        self.coords = self._coords

    @property
    def coords(self): return self._coords

    @coords.setter
    def coords(self, lrbt):
        self._coords = _lrbt(lrbt, *self._size)
        w, h = self._size
        self.pixelCoords = coordTr(self._coords, [w-1, h-1])
        self.plotCoords = coordTr(self._coords, [w-1, h-1], True)
        self.stale = True

    @property
    def units(self):
        "Calculate plot scales"
        px = self.pixelCoords
        p0 = px((0, 0))
        p1 = px((1, 1))
        return p1[0] - p0[0], p1[1] - p0[1] 

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
        return Series(pos).config(marker=text)

    def xtick(self, dx, ends=None, marker=9, **kwargs):
        param = (ends if ends else self._coords[:2]) + [dx]
        return Series._tick(param, marker, **kwargs)

    def ytick(self, dy, ends=None, marker=9, **kwargs):
        param = (ends if ends else self._coords[2:]) + [dy]
        return Series._tick(param, marker, True, **kwargs)

    def _drawAxis(self, srf, n, x, stroke, weight):
        "Draw the axes onto the plot surface"
        x0, x1 = x
        x0, x1 = [(0,x0), (0,x1)] if n else [(x0,0), (x1,0)]
        pygame.draw.line(srf, stroke, self.pixelCoords(x0), self.pixelCoords(x1), weight)

    def _grid(self, n, interval, xends=None, yends=None, stroke="grey", weight=1):
        "Set the x or y gridlines"
        if interval is False: cfg = None
        else:
            if xends is None: xends = self._coords[:2]
            if yends is None: yends = self._coords[2:]
            cfg = dict(interval=interval, xends=xends,
                yends=yends, stroke=stroke, weight=weight)
        if n: self._ygrid = cfg
        else: self._xgrid = cfg
        self.stale = True
        return self
    
    def grid(self, dx=None, dy=None, xends=None, yends=None, stroke="grey", weight=1):
        "Set both x and y gridlines"
        if dx is not None: self._grid(0, dx, xends, yends, stroke, weight)
        if dy is not None: self._grid(1, dy, xends, yends, stroke, weight)
        return self

    def _drawGrid(self, srf, n, cfg):
        "Draw gridlines"
        s = rgba(cfg["stroke"])
        w = cfg["weight"]
        x, x1 = cfg["yends" if n else "xends"]
        y0, y1 = cfg["xends" if n else "yends"]
        dx = cfg["interval"]
        while x <= x1:
            if n:
                p0 = [y0, x]
                p1 = [y1, x]
            else:
                p0 = [x, y0]
                p1 = [x, y1]
            pygame.draw.line(srf, s, self.pixelCoords(p0), self.pixelCoords(p1), w)
            x += dx

    def render(self):
        "Render the plot as a surface"
        srf = Image(self._size, self.bg).image
        if self._xgrid: self._drawGrid(srf, 0, self._xgrid)
        if self._ygrid: self._drawGrid(srf, 1, self._ygrid)
        if self._xaxis: self._drawAxis(srf, 0, *self._xaxis)
        if self._yaxis: self._drawAxis(srf, 1, *self._yaxis)
        for k in self._keys: self._series[k].draw(srf, self.pixelCoords)
        return srf


class PlotSprite(Plot, BaseSprite): pass


class Locus(Shape):
    "Class for drawing point sequences directly to the canvas"
    snapshot = None

    def __init__(self, data, lrbt, param):
        self.data = data
        self.lrbt = lrbt
        self.param = param
        self.vars = {}

    def _getCoordTr(self):
        w, h = sz = self.canvas.size
        return coordTr(_lrbt(self.lrbt, *sz), [w-1, h-1]) 

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
        pts = d if type(d) in (list, tuple) else locus(d, self.param, **self.vars)
        pts = [tr(p) for p in pts]
        pts = [(x + x0, y + y0) for (x, y) in pts]
        if len(pts) > 1:
            wt = self.weight
            return pygame.draw.lines(srf, self.stroke, False, pts, wt).inflate(wt, wt)
        else: return pygame.Rect(0,0,0,0)

    def pointGen(self):
        "Generate a sequence of points using canvas pixel coordinates"
        d = self.data
        pts = d if type(d) in (list, tuple) else locus(d, self.param, **self.vars)
        tr = self._getCoordTr()
        for p in pts: yield tr(p)

    @property
    def pointList(self):
        return list(self.pointGen())
