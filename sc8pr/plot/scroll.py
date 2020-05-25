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

from sc8pr import Image, BOTTOMLEFT, TOPRIGHT
from sc8pr.gui.slider import Slider

class ScrollBars:
    sliderBg = "#f0f0f0"
    sliderWidth = 16
    knobColor = "#cdcdcd"

    def __init__(self, cv, size=None):
        vw, vh = size if size else cv.size
        sw, sh = cv.scrollSize
        self.bars = []
        if sw > vw:
            self.bars.append(self.makeSlider(cv, 0, vw, sw, vh, sh > vh).config(dim=0, pos=(0, cv.height)))
        if sh > vh:
            self.bars.append(self.makeSlider(cv, 1, vh, sh, vw).config(dim=1, pos=(cv.width, 0)))
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
            val=-cv._scroll[dim], dim=dim, _scrollAdjust=False)
        return gr
    
    @staticmethod
    def sliderChange(s, ev):
        cv = s.canvas
        x, y = cv._scroll
        z = round(-s.val)
        if s.dim: cv.scrollTo(x, z)
        else: cv.scrollTo(z, y)
        setattr(ev, "dim", "xy"[s.dim])
        setattr(ev, "handler", "onscroll")
        cv.bubble("onscroll", ev)
