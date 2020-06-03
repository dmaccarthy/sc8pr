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


import pygame
from pygame.constants import K_LEFT, K_RIGHT, K_UP, K_DOWN
from sc8pr import Canvas, Image, Graphic
from sc8pr.util import tall
from sc8pr.geom import sigma, delta

CLICK = 0
SCROLL = 1
DRAG = 2
KEY = 3

def _knobDrag(knob, ev):
    "Handle drag events on the slider's 'knob' object"
    slider = knob.canvas
    if knob._dragRel is None:
        knob._dragRel = delta(knob.rect.center, ev.pos)
    if slider._lastButton in slider.allowButton:
        x = pygame.event.Event(pygame.USEREVENT, pos=sigma(ev.pos, knob._dragRel))
        v = slider._val
        slider.val = slider._eventValue(x)
        x = slider.val
        setattr(ev, "target", slider)
        if x != v:
            setattr(ev, "method", DRAG)
            slider.bubble("onchange", ev)

def _knobRelease(knob, ev): knob._dragRel = None


class Slider(Canvas):
    "A numerical slider GUI control"
    _lastButton = None
    focusable = True
    allowButton = 1, 4, 5
    methodNames = ["Click", "Scroll", "Drag", "Key"]

    def __init__(self, size=(128,16), knob="grey", lower=0, upper=1, steps=0):
        super().__init__(size)
        self.steps = steps
        if not isinstance(knob, Graphic): knob = Image(self._knobSize(), knob)
        self += knob.bind(ondrag=_knobDrag, onrelease=_knobRelease)
        self.knob = knob.config(_dragRel=None)
        if upper < lower:
            self._flip = True
            upper, lower = lower, upper
        else: self._flip = False
        self.lower = lower
        self.upper = upper
        self.val = lower

    def _knobSize(self):
        w, h = self.size
        a = min(w, h)
        if self.steps:
            b = round(max(w, h) / (1 + self.steps)) 
            b = max(a, b)
            w, h = (a, b) if h > w else (b, a)
        else: w = h = a
        return w, h

    @property
    def val(self): return self._val

    @val.setter
    def val(self, val):
        "Change the current value of the slider"
        val = max(self.lower, min(self.upper, val))
        x = self._round((val - self.lower) / (self.upper - self.lower))
        self._val = self._calc(x)
        if self._flip: x = 1 - x
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

    def _eventValue(self, ev):
        "Determine a numerical value from the event coordinates"
        dim = tall(*self.size)
        wh = self.knob.size[dim] + 2
        x = self._round((self.relXY(ev.pos)[dim] - wh / 2) / (self.size[dim] - wh))
        if self._flip: x = 1 - x
        return self._calc(x)

    def onmousedown(self, ev):
        "Handle click events on the slider canvas"
        self._lastButton = btn = ev.button
        if btn in self.allowButton:
            dim = tall(*self.size)
            lims = [self.lower, self.upper]
            if btn == 4: x = lims[dim]
            elif btn == 5: x = lims[1-dim]
            else: x = self._eventValue(ev)
            s = self.steps
            if not s: s = 100
            s = (self.upper - self.lower) / s
            v = self._val
            if x != v:
                if btn == 1 and ev.target is self: self.val = x
                elif x < v: self.val -= s
                else: self.val += s
                setattr(ev, "method", SCROLL if btn in (4,5) else CLICK)
                if ev: self.bubble("onchange", ev)

    def onkeydown(self, ev):
        "Handle arrow keys when the slider is focussed"
        if tall(*self.size):
            dx = 1 if ev.key == K_DOWN else -1 if ev.key == K_UP else 0
        else:
            dx = 1 if ev.key == K_RIGHT else -1 if ev.key == K_LEFT else 0
        if self._flip: dx = -dx
        if dx:
            cur = self._val
            s = self.steps
            if not s: s = 100
            self.val = self._val + dx * (self.upper - self.lower) / s
            if self._val != cur:
                setattr(ev, "method", KEY)
                self.bubble("onchange", ev)

    def resize(self, size):
        super().resize((16, size[1]))
