# Copyright 2015-2020 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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

from math import sqrt, floor, ceil
import pygame
from sc8pr import Image, Canvas, Sketch, Renderable, Graphic, BOTTOM, TOP, CENTER
from sc8pr.util import mix
from sc8pr.text import Text
from sc8pr.shape import Line, Polygon
from sc8pr.misc.plot import _lrbt
from sc8pr.plot.scroll import ScrollBars


def _str2gr(text, x, y, **kwargs):
    xy = dict(x=x, y=y)
    return PText(text.format(**xy)).config(**kwargs)

def _autoH(lrbt, width):
    return round(width * (lrbt[3] - lrbt[2]) / (lrbt[1] - lrbt[0]))


class _PCanvas:
    _lrbt = None
    _scrollSize = None
    _scrollbars = None
    _units = 1, 1, 1, True

    @property
    def units(self): return self._units[:2]

    @property
    def unit(self): return self._units[2]

    @property
    def clockwise(self): return self._units[3]

    @property
    def middle(self):
        l, r, b, t = self.lrbt
        return (l + r) / 2, (b + t) / 2

    @property
    def topleft(self): return self.cs(0, 0)

    @property
    def top(self): return self.topleft[1]

    @property
    def left(self): return self.topleft[0]

    @property
    def bottomright(self):
        w, h = self.scrollSize
        return self.cs(w-1, h-1)

    @property
    def bottom(self): return self.bottomright[1]

    @property
    def right(self): return self.bottomright[0]

    @property
    def topright(self):
        return tuple(self.lrbt[i] for i in (3, 1))

    @property
    def bottomleft(self):
        return tuple(self.lrbt[i] for i in (2, 0))

    @property
    def lrbt(self):
        l, t = self.topleft
        r, b = self.bottomright
        return l, r, b, t

    @property
    def scrollSize(self):
        return self.size if self._scrollSize is None else self._scrollSize

    def setCoords(self, lrbt=None, scrollSize=None):
        self._scrollSize = scrollSize
        w, h = self.scrollSize 
        if lrbt:
            if len(lrbt) != 4: lrbt = _lrbt(lrbt, w, h)
            self._lrbt = lrbt
            l, r = lrbt[:2]
            sx = (w - 1) / (r - l)
            dx = sx * l
            b, t = lrbt[2:]
            sy = (h - 1) / (b - t)
            dy = sy * t
            self._cs = lambda p: ((p[0] + dx) / sx, (p[1] + dy) / sy)
            self._px = lambda p: (sx * p[0] - dx, sy * p[1] - dy)
            p0 = self.px(0, 0)
            p1 = self.px(1, 1)
            p0, p1 = p1[0] - p0[0], p1[1] - p0[1]
            self._units = p0, p1, sqrt(abs(p0 * p1)), p0 * p1 > 0
        if self._scrollbars: self -= self._scrollbars
        self._scrollbars = ScrollBars(self)
        return self

    def draw(self, srf=None, mode=3):
        s = self._scrollbars
        if s: self += s 
        return super().draw(srf, mode)

    def transform(self, pts, **kwargs):
        tr = self.cs if kwargs.get("invert") else self.px
        for pt in pts: yield(tr(*pt))

    def scroll(self, dx, dy):
        x, y = self._scroll
        self._scroll = x + dx, y + dy
        for gr in self:
            if gr._scrollAdjust:
                x, y = gr.pos
                gr.pos = x -dx, y - dy

    @property
    def scrollPos(self): return self._scroll

    @scrollPos.setter
    def scrollPos(self, pt):
        self.scrollTo(*pt)

    def scrollTo(self, x=0, y=0):
        dx, dy = self._scroll
        return self.scroll(x-dx, y-dy)

    def scrollSnapshot(self):
        "Take a snapshot of the entire scroll region"
        cv = PCanvas(self.scrollSize, self.lrbt, bg=self.bg)
        cv.config(weight=self.weight, border=self.border)        
        for gr in list(self): gr.setCanvas(cv)
        img = cv.snapshot()
        for gr in list(cv): gr.setCanvas(self)
        return img

    def gridlines(self, lrbt, step=1, axis=None, **kwargs):
        "Draw gridlines and optional coordinate axes"
        style = {"weight":1, "stroke":"lightgrey"}
        style.update(kwargs)
        if type(step) in (int, float): dx = dy = step
        else: dx, dy = step
        x0, x1, y0, y1 = lrbt
        px = self.px
        if dx:
            x = x0
            while x < x1 + dx / 2:
                self += Line(px(x, y0), px(x, y1)).config(**style)
                x += dx
        if dy:
            while y0 < y1 + dy / 2:
                self += Line(px(x0, y0), px(x1, y0)).config(**style)
                y0 += dy
        return self if axis is None else self.axis(lrbt, **axis)

    def axis(self, x=None, y=None, **kwargs):
        "Draw coordinate axes"
        style = {"weight":2, "stroke":"black"}
        style.update(kwargs)
        px = self.px
        if y is None and len(x) == 4:
            x, y = x[:2], x[2:]
        if x: self += Line(px(x[0], 0), px(x[1], 0)).config(**style)
        if y: self += Line(px(0, y[0]), px(0, y[1])).config(**style)
        return self

    def series(self, points, markers=1, shift=(0, 0), **kwargs):
        "Create a list of graphics items from a data series"
        i = 0
        dx, dy = shift
        px = self.px
        items = []
        for x, y in points:
            t = type(markers)
            if t in (int, float):
                items.append(PBar(x, y, markers).config(**kwargs))
            else:
                if t is str: gr = _str2gr(markers, x, y, **kwargs)
                else:
                    try:
                        gr = markers[i]
                        if type(gr) is str: gr = _str2gr(gr, x, y, **kwargs)
                    except: gr = PImage(markers)
                pos = x + dx, y + dy
                if isinstance(gr, _PObject): gr.update(*pos)
                else: gr.config(pos=px(*pos))
                items.append(gr)
            i += 1
        return items

    def data(self, series, data, shift=(0, 0)):
        "Modify the data for a data series"
        dx, dy = shift
        px = self.px
        series = iter(series)
        for x, y in data:
            gr = next(series)
            pos = x + dx, y + dy
            if isinstance(gr, _PObject): gr.update(*pos)
            else: gr.config(pos=px(*pos))
        return self

    def _scrollEvent(self):
        "Send SCROLL event to Canvas after resizing"
        if self._scrollbars.bars:
            sk = self.sketch
            evMgr = sk.evMgr
            ev = pygame.event.Event(pygame.USEREVENT, focus=evMgr.focus, hover=evMgr.hover, target=sk, handler="onscroll")
            self.bubble("onscroll", ev)


class PCanvas(_PCanvas, Canvas):
    
    def __init__(self, size, lrbt=None, scrollSize=None, bg=None):
        if type(size) is int:
            size = size, _autoH(lrbt, size)
        super().__init__(size, bg)
        if lrbt or scrollSize: self.setCoords(lrbt, scrollSize)

    def resize(self, size):
        self.scrollTo()
        super().resize(size)
        self.setCoords(self._lrbt, self._scrollSize)
        self._scrollEvent()

    @staticmethod
    def simple(size, lrbt, step=1):
        return PCanvas(size, lrbt).gridlines(lrbt, step, {})


class PSketch(_PCanvas, Sketch):
    
    def __init__(self, size=(512, 288), lrbt=None, scrollSize=None):
        if type(size) is int:
            size = size, _autoH(lrbt, size)
        if lrbt or scrollSize:
            self._defer_coords = lrbt, scrollSize
        super().__init__(size)

    def resizeCoords(self, ev):
        scrollSize = None
        if self._scrollSize:
            if self.resizeContent:
                w, h = ev.originalSize 
                f = (self.width / w + self.height / h) / 2
                w, h = self._scrollSize
                scrollSize = f * w, f * h
            else: scrollSize = self._scrollSize
        self.setCoords(self._lrbt, scrollSize)
        self._scrollEvent()


class _PObject:
    autoPositionOnResize = _scrollAdjust = False
    theta = 0
    csPos = 0, 0

    @property
    def pos(self):
        cv = self.canvas
        return cv.px(*self.csPos) if cv else self.csPos

    @pos.setter
    def pos(self, pos):
        cv = self.canvas
        if cv: pos = cv.cs(*pos)
        self.csPos = pos

    @property
    def angle(self):
        cv = self.canvas
        return self.theta if cv is None or cv.clockwise else -self.theta

    @angle.setter
    def angle(self, a):
        cv = self.canvas
        self.theta = a if cv is None or cv.clockwise else -a
    
    def update(self, x, y): self.csPos = x, y


class PBar(_PObject, Renderable):
    fill = "blue"
    stroke = "black"
    weight = 1
    contains = Graphic.contains

    @property
    def anchor(self):
        return BOTTOM if self._xy[1] >= 0 else TOP

    @property
    def csPos(self): return self._xy[0], 0

    @property
    def pos(self):
        x, y = self._xy
        x1, y1 = self.canvas.px(x, 0)
        return x1, floor(y1) if y < 0 else ceil(y1)

    @pos.setter
    def pos(self, xy): pass

    @csPos.setter
    def csPos(self, xy): pass

    def __init__(self, x, y, barWidth=1):
        self._xy = x, y
        self._barWidth = barWidth

    def update(self, x, y): self._xy = x, y

    def render(self):
        y = self._xy[1]
        cv = self.canvas
        u = cv.units
        w = round(abs(u[0] * self._barWidth))
        h = round(abs(u[1] * y))
        wt = round(self.weight)
        img = Canvas((w, h + 1), self.fill).config(weight=wt, border=self.stroke)
        return img.snapshot().original


class PImage(_PObject, Image): pass
class PText(_PObject, Text): pass
