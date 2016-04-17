# Copyright 2015-2016 D.G. MacCarthy <devwigs@gmail.com>
#
# This file is part of WIGS.
#
# WIGS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# WIGS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with WIGS.  If not, see <http://www.gnu.org/licenses/>.


import pygame
from wigs.widgets import Slider, Widget, Container
from wigs.image import Image
from wigs.gui import GuiEvent
from wigs.util import CROSS
from math import atan, pi


def hsvToRgb(h, s, v):
    if s:
        if h < 0: h = 0
        h /= 60
        i = int(h)
        f = h - i
        p = v * (1 - s)
        q = v * (1 - s * f)
        t = v * (1 - s * ( 1 - f ))
        if i == 0: c = (v, t, p)
        elif i == 1: c = (q, v, p)
        elif i == 2: c = (p, v, t)
        elif i == 3: c = (p, q, v)
        elif i == 4: c = (t, p, v)
        else: c = (v, p, q)
    else:
        c = (v, v, v)
    return round(255 * c[0]), round(255 * c[1]), round(255 * c[2])


def rgbToHsv(r, g, b):
    v = max(r, g, b)
    dv = v - min(r, g, b)
    if v == 0: return -1, 0, 0
    s = dv / v
    if s == 0: return -1, 0, v/255
    if r == v: h = (g - b) / dv
    elif g == v: h = 2 + (b - r) / dv
    else: h = 4 + (r - g) / dv
    h *= 60
    if h < 0: h += 360
    return h, s, v/255


class Hue(Widget):
    enabled = True
    state = 1
    cursorId = CROSS

    @staticmethod
    def image(size=(256,16), val=1.0, sat=None):
        s, v = sat, val
        w, h = size
        vert = h > w
        if vert: w, h = h, w
        img = Image(size, (255,0,0))
        pxArr = pygame.PixelArray(img.surface)
        for x in range(w):
            for y in range(h):
                if sat == None: s = y / (h - 1)
                if val == None: v = y / (h - 1)
                c = hsvToRgb(360.0 * x / (w-1), s, v)
                if vert: pxArr[y, x] = c
                else: pxArr[x, y] = c
        del pxArr
        return img

    @staticmethod
    def wheel(radius=63, val=1.0):
        w = 2 * radius + 1
        img = Image((w, w))
        pxArr = pygame.PixelArray(img.surface)
        for x in range(w):
            for y in range(w):
                dx = x - radius
                dy = y - radius
                r = (dx*dx + dy*dy) ** 0.5
                if r <= radius:
                    a = atan(dy/dx) if dx else (pi / (2 if dy>0 else -2)) if dy else 0
                    if dx < 0: a += pi
                    if a < 0: a += 2 * pi
                    pxArr[x, y] = hsvToRgb(a * 180 / pi, r/radius, val)
        return img

    def __init__(self, name, size=(128,128), posn=(0,0), val=1.0, border=Slider.border, borderColor=Slider.borderColor):
        super().__init__(name, posn)
        self.size = size
        self.radius = min(size) // 2 - 3
        self.img = img = (self.image(self.size, val), self.wheel(self.radius, val))
        if size != img[1].size: self.img = img[0], img[1].crop(size)
        if border:
            for img in self.img:
                img.borderInPlace(border, borderColor)

    def getImage(self, n=0): return self.img[self.state]

    def _event(self, ev):
        if ev.type == GuiEvent.MOUSEDOWN:
            change = True
            h, s = ev.relPosn(self.state)
            if self.state:
                r = self.radius
                x, y = h/r, s/r
                s = (x*x + y*y) ** 0.5
                if s <= 1:
                    if x or y:
                        h = 180 * atan(y/x) / pi if x else (90 if y > 0 else 270)
                        if x < 0: h += 180
                        if h < 0: h += 360
                    else:
                        h = 0
                else:
                    change = False
            else:
                h *= 360.0 / (self.getWidth() - 1)
                if h >= 360: h -= 360
                s /= self.getHeight() - 1
            if change:
                self.hsv = h, s, 1.0
                ev.type = GuiEvent.CHANGE
        return self._onEvent(ev)


class ColorPicker(Container):
    focusable = True

    def __init__(self, name, width=192, posn=(0,0), color=(192,128,255), space=-1, font=None):
        super().__init__(name, posn)
        if font: self.font = font
        self.render(width, color, space)
        self.wheel = 1

    def render(self, width=192, color=(192,128,255), space=-1):
        self.widgets = []
        self.space = space
        sz = width, None
        name = self.name + "_"
        data = 0, 255, 128
        self.r = Slider(data, sz, name+"Red", step=1, frmt="{:d}", border=1, fgColor=(255,0,0), font=self.font)
        self.g = Slider(data, sz, name+"Green", step=1, frmt="{:d}", border=1, fgColor=(0,255,0), font=self.font)
        self.b = Slider(data, sz, name+"Blue", step=1, frmt="{:d}", border=1, fgColor=(0,0,255), font=self.font)
        self.hue = Hue(name+"HueSat", (width, width))
        self.val = Slider((0,1,1), sz, name+"Val", handle=0.2, border=1, fgColor=(224,224,224), font=self.font)
        self.hue.posn = self.val.below(space)
        self.r.posn = self.hue.below(space)
        self.g.posn = self.r.below(space)
        self.b.posn = self.g.below(space)
        self.place(self.hue, self.val, self.r, self.g, self.b)
        self.rgb = color

    @property
    def rgb(self): return self._rgb

    @rgb.setter
    def rgb(self, rgb):
        self.r.value, self.g.value, self.b.value = rgb
        self.val.bgColor = self._rgb = rgb
        self.val.value = self.hsv[2] ** 2
        self.val.render()
        for s in (self.r, self.g, self.b, self.val): s.render()

    @property
    def hsv(self):
        r, g, b = self.rgb
        return rgbToHsv(r, g, b)

    @hsv.setter
    def hsv(self, hsv):
        h, s, v = hsv
        self.rgb = hsvToRgb(h, s, v)

    @property
    def wheel(self): return self.hue.state

    @wheel.setter
    def wheel(self, w): self.hue.state = int(w)

    def toggleWheel(self): self.wheel = 1 - self.wheel

    def _event(self, ev):
        if ev.target == self.hue:
            if ev.type == GuiEvent.CHANGE:
                self.hsv = self.hue.hsv
            else: return(ev)
        elif ev.target == self.val:
            h, s, v = self.hsv
            v = self.val.value ** 0.5
            self.hsv = h, s, v
        else:
            self.rgb = self.r.value, self.g.value, self.b.value
        if ev.target != self: ev.type = GuiEvent.CHANGE
        return self._onEvent(ev)
