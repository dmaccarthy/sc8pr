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


import pygame
from pygame.constants import K_ESCAPE, K_BACKSPACE, K_LEFT, K_RIGHT,\
    K_DELETE, K_HOME, K_END, KMOD_CTRL, KMOD_ALT
from sc8pr.text import Text, Font
from sc8pr.util import style, rgba
from sc8pr.geom import vec2d, sigma


class TextInput(Text):
    """Editable text GUI control:
    handles onclick, onkeydown, onblur; triggers onchange, onaction"""
    focusable = True
    cursorTime = 1.0
    cursorOn = 0.35
    promptColor = rgba("#d0d0d0")
    padding = 4
    allowButton = 1,
    _cursorX = 0
    _scrollX = 0

    def __init__(self, data="", prompt=None):
        super().__init__(str(data).split("\n")[0])
        self.cursor = len(self.data)
        self.cursorStatus = False
        self.prompt = prompt

    def _startCursor(self):
        self.stale = True
        self.cursorStatus = True
        self.cursorStart = self.sketch.frameCount

    def draw(self, srf):
        if self.focussed:
            sk = self.sketch 
            n = (sk.frameCount - self.cursorStart) / sk.frameRate
            if n > self.cursorTime: self._startCursor()
            else:
                c =  n < self.cursorOn
                if c is not self.cursorStatus:
                    self.cursorStatus = c
                    self.stale = True
        elif self.cursorStatus:
            self.cursorStatus = False
            self.stale = True
        return super().draw(srf)

    def render(self):
        "Render the text as an Image"
        font = Font.get(self.font, self.fontSize, self.fontStyle)
        try: focus = self is self.sketch.evMgr.focus
        except: focus = False
        if self.prompt and not self.data and not focus:
            color = self.promptColor
            text = self.prompt
        else: 
            color = self.color
            text = self.data
        srf = font.render(text, True, color)
        srf = style(srf, self.bg, self.border, self.weight, self.padding)
        x = font.size(text[:self.cursor])[0]
        p = self.padding
        x += p
        self._cursorX = x
        if self.cursorStatus:
            h = srf.get_height()
            pygame.draw.line(srf, self.color, (x,p), (x,h-1-p), 2)
        return srf

    def onkeydown(self, ev):
        if ev.mod & (KMOD_CTRL | KMOD_ALT): return
        self._startCursor()
        u = ev.unicode
        if u in ("\n", "\r", "\t"):
            self.blur()
            return self.onblur(ev)
        d = self.data
        n = len(d)
        cursor = self.cursor
        k = ev.key
        change = True
        self.stale = True
        if d and k == K_ESCAPE:
            self.data = ""
            cursor = 0
        elif cursor and k == K_BACKSPACE:
            self.data = d[:cursor-1] + d[cursor:]
            cursor -= 1
        elif cursor < n and k == K_DELETE:
            self.data = d[:cursor] + d[cursor+1:]
        elif k >= 32 and k < 127:
            self.data = d[:cursor] + u + d[cursor:]
            cursor += 1
        else: change = False
        self.cursor = cursor
        if change: return self.bubble("onchange", ev)
        if cursor:
            if k == K_LEFT: cursor -= 1
            elif k == K_HOME: cursor = 0
        if cursor < n:
            if k == K_RIGHT: cursor += 1
            elif k == K_END: cursor = n
        self.cursor = cursor

    def _widthTo(self, i):
        font = Font.get(self.font, self.fontSize, self.fontStyle)
        d = self.data
        return (font.size(d[:i])[0] + font.size(d[:i+1])[0]) // 2

    def onclick(self, ev):
        if ev.button in self.allowButton:
            self._startCursor()
            x = self.relXY(ev.pos)[0] - self.padding
            n = len(self.data)
            i = 0
            while i < n and x > self._widthTo(i): i += 1
            self.cursor = i
            self.stale = True
        elif not hasattr(self, "cursorStart"): self.blur()

    def onblur(self, ev):
        if not self.data: self.stale = True
        if hasattr(self, "cursorStart"): del self.cursorStart
        self.bubble("onaction", ev)

    def scroll(self, pix=None, rel=True):
        # Calculate optimal scroll
        if pix is None: pix = self.focussed
        if pix is False:
            pix, rel = 0, False
        elif pix is True:
            a = self.angle
            if a not in (0, 90): raise ValueError("Cannot autoscroll unless angle is a 0 or 90")
            width = (self.canvas.height if a else self.canvas.width) - 2
            if self.width <= width:
                pix, rel = 0, False
            else:
                rel = True
                x = (self.anchor & 12) // 4 if a else (self.anchor & 3)
                x = self.pos[1 if a else 0] - x * self.width / 2 + self._cursorX
                if x < 0: pix = -x
                elif x > width: pix = width - x
                else: pix, rel = 0, True

        # Set scrolling attributes
        if rel:
            self._scrollX += pix
            dx = pix
        else:
            dx = pix - self._scrollX
            self._scrollX = pix
        self.pos = sigma(self.pos, vec2d(dx, self.angle))
        return self
