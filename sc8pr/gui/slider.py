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


from pygame.constants import K_LEFT, K_RIGHT, K_UP, K_DOWN
from sc8pr import Canvas, Image, Graphic
from sc8pr.util import tall


def ondrag(knob, ev):
    "Handle drag events on the slider's 'knob' object"
    slider = knob.canvas
    x = slider.eventValue(ev)
    setattr(ev, "target", slider)
    if x != slider._val:
        slider.value = x
        slider.bubble("onchange", ev)


class Slider(Canvas):
    "A numerical slider GUI control"
    focusable = True

    def __init__(self, size=(128,16), knob="grey", lower=0, upper=1, steps=0):
        super().__init__(size)
        if not isinstance(knob, Graphic): knob = Image(bg=knob)
        w, h = size
        kwargs = {"width":w} if h > w else {"height":h}
        self += knob.bind(ondrag).config(**kwargs)
        self.knob = knob
        self.steps = steps
        if upper < lower:
            self.flip = True
            upper, lower = lower, upper
        else: self.flip = False
        self.lower = lower
        self.upper = upper
        self.value = lower

    @property
    def value(self): return self._val

    @value.setter
    def value(self, val):
        "Change the current value of the slider"
        val = max(self.lower, min(self.upper, val))
        x = self._round((val - self.lower) / (self.upper - self.lower))
        self._val = self._calc(x)
        if self.flip: x = 1 - x
        knob = self.knob
        dim = tall(*self.size)
        wh = knob.size[dim] + 2
        w, h = self.size
        knob.pos = (w / 2, wh / 2 + (h - wh) * x) if dim else (wh / 2 + (w - wh) * x, h / 2)

    def _round(self, x):
        s = self.steps
        return round(s * x) / s if s else x

    def _calc(self, x):
        return self.lower + min(max(0, x), 1) * (self.upper - self.lower)

    def eventValue(self, ev):
        "Determine a numerical value from the event coordinates"
        dim = tall(*self.size)
        wh = self.knob.size[dim] + 2
        x = self._round((self.relXY(ev.pos)[dim] - wh / 2) / (self.size[dim] - wh))
        if self.flip: x = 1 - x
        return self._calc(x)

    def onclick(self, ev):
        "Handle click events on the slider canvas"
        x = self.eventValue(ev)
        s = self.steps
        if not s: s = 100
        s = (self.upper - self.lower) / s
        v = self._val
        if x != v:
            if x < v: self.value -= s
            else: self.value += s
            if ev: self.bubble("onchange", ev)

    def onkeydown(self, ev):
        "Handle arrow keys when the slider is focussed"
        if tall(*self.size):
            dx = 1 if ev.key == K_DOWN else -1 if ev.key == K_UP else 0
        else:
            dx = 1 if ev.key == K_RIGHT else -1 if ev.key == K_LEFT else 0
        if self.flip: dx = -dx
        if dx:
            cur = self._val
            s = self.steps
            if not s: s = 100
            self.value = self._val + dx * (self.upper - self.lower) / s
            if self._val != cur: self.bubble("onchange", ev)
