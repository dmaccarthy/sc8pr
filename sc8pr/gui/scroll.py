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
from sc8pr.gui.slider import Slider, Knob
from sc8pr import Image, Canvas, Sketch, BOTTOMLEFT, TOPRIGHT

CANVAS = 1
SCROLL = 2
BOTH = 3    # Same as sc8pr.BOTH

class ScrollBars:
    "Scroll bar slider controls for a scrolling canvas"
    sliderBg = "#e0e0e0"
    sliderWidth = 16

    def __iter__(self):
        for b in self.bars: yield b

    def __init__(self, cv, size):
        "Create vertical and horizontal scroll bars for canvas"
        self.canvas = cv

        # Get dimensions
        canvasW, canvasH = size
        scrollW, scrollH = cv.scrollSize
        thickness  = max(min(self.sliderWidth, (min(size) - 1) // 8), 4)

        # Calculate which bars are required and remaining canvas size
        bars = 0
        if canvasW < scrollW:
            bars += 1
            canvasH -= thickness
        if canvasH < scrollH:
            bars += 2
            canvasW -= thickness
            if bars == 2 and canvasW < scrollW:
                bars += 1
                canvasH -= thickness

        # Create the scroll bars
        self.bars = []
        x, y = cv._scroll
        if bars & 1:
            sb = self.makeScrollBar(0, bars, thickness, canvasW, scrollW)
            self.bars.append(sb.config(val=-x, anchor=BOTTOMLEFT, corner=(0, canvasH + thickness)))
        if bars & 2:
            sb = self.makeScrollBar(1, bars, thickness, canvasH, scrollH)
            self.bars.append(sb.config(val=-y, anchor=TOPRIGHT, corner=(canvasW + thickness, 0)))

    def makeScrollBar(self, dim, bars, thickness, canvasW, scrollW):
        "Create one of the scroll bars"

        # Calculate slider and knob size
        sliderW = canvasW + (thickness if dim == 1 and bars == 3 or bars == 1 else 0)
        knobW = max(2, round(sliderW * canvasW / scrollW))
        knobSize = (thickness, knobW) if dim else (knobW, thickness)
        sliderSize = (thickness, sliderW) if dim else (sliderW, thickness)

        # Make knob and slider
        maxScroll = scrollW - canvasW
        kwargs = dict(upper = -maxScroll, steps = max(2, maxScroll))
        slider = Slider(sliderSize, Knob(knobSize), **kwargs).bind(onchange=self.sliderChange)
        if dim == 0: slider.config(reverseWheel = True)
        return slider.config(bg=self.sliderBg, dim=dim, scrollable=False, weight=0)
    
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


class BaseScroll(Canvas):
    "Base class for scrolling Canvas and Sketch subclasses"
    _scroll = 0, 0
    resizeContent = False
    resizeScroll = False

    @property
    def scrollPos(self): return self._scroll

    @property
    def scrollSize(self): return self._scrollSize

    @scrollSize.setter
    def scrollSize(self, scrollSize):
        self._scrollReset()
        self._scrollInit(self.size, scrollSize)
        if self.resizeContent and self.coordSys: self._updateCS()

    def scale(self, sx, sy=None, mode=CANVAS):
        if mode & CANVAS: super().scale(sx, sy)
        if mode & SCROLL:
            w, h = self._scrollSize
            self.scrollSize = round(sx * w), round(h * (sy if sy else sx))

    def draw(self, srf=None, mode=3):
        "Move scroll bars to top layer before drawing"
        for sb in self._scrollBars:
            if sb in self: sb.layer = -1
            else:
                self += sb
                c = getattr(sb, "corner", None)
                if c:
                    sb.config(pos=c)
                    del sb.corner
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

    def snapshot(self, viewport=True):
        "Take a snapshot of the entire scroll region"
        if viewport: return super().snapshot()
        cv = Canvas(self.scrollSize, bg=self.bg)
        if self.coordSys:
            cv.attachCS(*self.coordSys._args)
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


class ScrollCanvas(BaseScroll):

    def __init__(self, size, scrollSize=None, bg=None):
        super().__init__(size, bg)
        self._scrollInit(size, scrollSize)

    def resize(self, size, resizeContent=None):
        self._scrollReset()
        super().resize(size, resizeContent)
        self._scrollBars = ScrollBars(self, self._size)
        self._scrollEvent()


class ScrollSketch(BaseScroll, Sketch):
    _fixedAspect = False

    def __init__(self, size=(512, 288), scrollSize=None):
        super().__init__(size)
        self._scrollInit(size, scrollSize)

    def resize(self, size, mode=None):
        self._scrollReset()
        super().resize(size, mode)
        self._scrollBars = ScrollBars(self, self.size)
        self._scrollEvent()
