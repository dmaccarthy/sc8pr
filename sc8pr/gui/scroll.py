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
from sc8pr.gui.slider import Slider
from sc8pr import Image, Canvas, Sketch, BOTTOMLEFT, TOPRIGHT
from sc8pr._cs import _makeCS


class ScrollBars:
    "Scroll bar slider controls for a scrolling canvas"
    sliderBg = "#f0f0f0"
    sliderWidth = 16
    knobColor = "#cdcdcd"

    def __init__(self, cv, size):
        vw, vh = size # if size else cv.size
        sw, sh = cv.scrollSize
        self.bars = []
        if sw > vw:
            self.bars.append(self.makeSlider(cv, 0, vw, sw, vh, sh > vh).config(dim=0, pos=(0, vh))) # cv.height
        if sh > vh:
            self.bars.append(self.makeSlider(cv, 1, vh, sh, vw).config(dim=1, pos=(vw, 0))) # cv.width
        self.canvas = cv

    def __iter__(self):
        for b in self.bars: yield b

    def makeSlider(self, cv, dim, ch, sh, cw, other=False):
        "Create a vertical or horizontal scroll bar"
        w = min(self.sliderWidth, ch - 1, cw // 12)
        h = ch + 1 - (w if other and dim == 0 else 0)
        knob = round(ch * (h - 1) / sh)
        knob = Image((w, knob) if dim else (knob, w), self.knobColor)
        size = (w, h) if dim else (h, w)
        a = TOPRIGHT if dim else BOTTOMLEFT
        u = ch - sh - (w if other else 0)
        gr = Slider(size=size, knob=knob, upper=u).bind(onchange=self.sliderChange)
        gr.config(bg=self.sliderBg, anchor=a, weight=0,
            val=-cv._scroll[dim], dim=dim, scrollable=False)
        return gr
    
    @staticmethod
    def sliderChange(s, ev):
        cv = s.canvas
        x, y = cv._scroll
        z = round(-s.val)
        if s.dim: cv._scrollTo(x, z)
        else: cv._scrollTo(z, y)
        setattr(ev, "dim", "xy"[s.dim])
        setattr(ev, "handler", "onscroll")
        cv.bubble("onscroll", ev)


class _SCanvas(Canvas):
    "Base class for scrolling Canvas and Sketch subclasses"
    _scroll = 0, 0
    resizeContent = False
    resizeScroll = False

    def attachCS(self, lrbt, margin=0, size=None):
        "Base coordinate transformation on scroll size instead of actual size"
        self._cs, self._px = _makeCS(lrbt, size if size else self._scrollSize, margin)
        return self

    @property
    def scrollSize(self): return self._scrollSize

    @scrollSize.setter
    def scrollSize(self, scrollSize):
        self._scrollTo()
        self._scrollInit(self.size, scrollSize)

    def draw(self, srf=None, mode=3):
        "Move scroll bars to top layer before drawing"
        s = self._scrollBars
        if s: self += s 
        return super().draw(srf, mode)

    def _scrollBy(self, dx, dy):
        "Adjust scroll position by specified amounts"
        x, y = self._scroll
        self._scroll = x + dx, y + dy
        for gr in self:
            if gr.scrollable:
                x, y = gr.pos
                gr.pos = x -dx, y - dy

    def _scrollTo(self, x=0, y=0):
        "Adjust scroll position to specified location"
        dx, dy = self._scroll
        return self._scrollBy(x-dx, y-dy)

    def scrollSnapshot(self):
        "Take a snapshot of the entire scroll region"
        cv = Canvas(self.scrollSize, bg=self.bg)
        cv.config(weight=self.weight, border=self.border)        
        for gr in list(self):
            if gr not in self._scrollBars: gr.setCanvas(cv)
        img = cv.snapshot()
        for gr in list(cv): gr.setCanvas(self)
        return img

    def _scrollEvent(self):
        "Send SCROLL event to Canvas after resizing"
        sk = self.sketch
        if sk and self._scrollBars.bars:
            evMgr = sk.evMgr
            ev = pygame.event.Event(pygame.USEREVENT, focus=evMgr.focus, hover=evMgr.hover, target=sk, handler="onscroll")
            self.bubble("onscroll", ev)

    def _scrollInit(self, size, scrollSize):
        self._scrollSize = scrollSize if scrollSize else size
        self._scrollBars = ScrollBars(self, size)

    def _scrollReset(self):
        self._scrollTo()
        sb = self._scrollBars
        if sb: self.removeItems(*sb)


class ScrollCanvas(_SCanvas):

    def __init__(self, size, scrollSize=None, bg=None):
        super().__init__(size, bg)
        self._scrollInit(size, scrollSize)

    def resize(self, size, resizeContent=None):
        self._scrollReset()
        super().resize(size, resizeContent)
        self._scrollBars = ScrollBars(self, size)
        self._scrollEvent()


class ScrollSketch(_SCanvas, Sketch):
    _fixedAspect = False

    def __init__(self, size=(512, 288), scrollSize=None):
        super().__init__(size)
        self._scrollInit(size, scrollSize)

    def resize(self, size, mode=None):
        self._scrollReset()
        super().resize(size, mode)
        self._scrollBars = ScrollBars(self, self.size)
        self._scrollEvent()
