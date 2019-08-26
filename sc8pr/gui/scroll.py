# Copyright 2015-2019 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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


from sc8pr import Image, Canvas, Sketch, TOPRIGHT, BOTTOMLEFT
from sc8pr.gui.slider import Slider


class _SCanvas:
    sliders = None, None
    sliderBg = "#f0f0f0"
    sliderWidth = 16
    knobColor = "#cdcdcd"

    @property
    def scrollSize(self): return self._scrollSize

    @scrollSize.setter
    def scrollSize(self, size):
        "Add sliders to serve as scroll bars"

        # Remove old scroll bars
        for gr in self.sliders:
            if gr: gr.remove()

        # New scroll size
        cw, ch = self._size
        sw, sh = size if size else (0, 0)
        if sw < cw: sw = cw
        if sh < ch: sh = ch
        self._scrollSize = sw, sh

        # Make new scroll bars
        if sh > ch:
            sy = self._makeSlider(1, ch, sh, cw, sw > cw)
            self += sy
            self.scrollTo(self._scroll[0], -round(sy.val))
        else: sy = None
        if sw > cw:
            sx = self._makeSlider(0, cw, sw, ch, sh > ch)
            self += sx
            self.scrollTo(-round(sx.val), self._scroll[1])
        else: sx = None
        self.sliders = sx, sy
        self._posnSliders()

    def _makeSlider(self, dim, ch, sh, cw, other):
        "Create a vertical or horizontal scroll bar"
        w = min(self.sliderWidth, ch - 1)
        h = ch + 1 - (w if other and dim == 0 else 0)
        knob = round(ch * (h - 1) / sh)
        knob = Image((w, knob) if dim else (knob, w), self.knobColor)
        size = (w, h) if dim else (h, w)
        a = TOPRIGHT if dim else BOTTOMLEFT
        u = ch - sh - (w if other else 0)
        gr = Slider(size=size, knob=knob, upper=u).bind(onchange=self.sliderChange)
        gr.config(bg=self.sliderBg, anchor=a, weight=0,
            val=-self._scroll[dim], dim=dim, scrollable=False)
        return gr

    def _posnSliders(self):
        "Position the scroll bars at bottom and right of canvas"
        for gr in self.sliders:
            if gr: gr.pos = (self.width, 0) if gr.dim else (0, self.height)

    def _layerSliders(self):
        "Move scroll bars to top of canvas"
        for gr in self.sliders:
            if gr: gr.config(layer=-1)

    @staticmethod
    def sliderChange(slider, ev):
        "Event handler for slider ONCHANGE"
        cv = slider.canvas
        x = abs(round(slider.val))
        x = (cv._scroll[0], x) if slider.dim else (x, cv._scroll[1])
        cv.scrollTo(*x)
        cv._posnSliders()
        cv.bubble("onscroll", ev)

    def draw(self, srf=None, mode=3):
        "Move scroll bars to top before drawing"
        self._layerSliders()
        return super().draw(srf, mode)

    def dpos(self, x, y):
        w, h = self._scrollSize
        return x * (w - 1), y * (h - 1)


class ScrollCanvas(_SCanvas, Canvas):

    def __init__(self, image, bg=None):
        super().__init__(image, bg)
        self.scrollSize = None

    def resize(self, size, resizeContent=True):
        super().resize(size, resizeContent)
        w, h = self._scrollSize
        self.scrollSize = round(w), round(h)


class ScrollSketch(_SCanvas, Sketch):

    def __init__(self, size):
        super().__init__(size)
        self.scrollSize = None

    def resize(self, size, mode=None):
        self.scrollSize = None
        super().resize(size, mode)
