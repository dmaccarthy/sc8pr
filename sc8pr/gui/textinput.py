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


import pygame
from pygame.constants import K_ESCAPE, K_BACKSPACE, K_LEFT, K_RIGHT,\
    K_DELETE, K_HOME, K_END, KMOD_CTRL, KMOD_ALT
from sc8pr.text import Text, Font
from sc8pr.util import style, rgba


class TextInput(Text):
    """Editable text GUI control:
    handles onclick, onkeydown, onblur; triggers onchange, onaction"""
    focusable = True
    cursorTime = 1.0
    cursorOn = 0.35
    promptColor = rgba("#f0f0f0")

    def __init__(self, data="", prompt=None):
        super().__init__(str(data).split("\n")[0])
        self.cursor = len(self.data)
        self.cursorStatus = False
        self.prompt = prompt

    def startCursor(self):
        self.stale = True
        self.cursorStatus = True
        self.cursorStart = self.sketch.frameCount

    def draw(self, srf):
        if self.focussed:
            sk = self.sketch 
            n = (sk.frameCount - self.cursorStart) / sk.frameRate
            if n > self.cursorTime: self.startCursor()
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
        if self.cursorStatus:
            x, h = font.size(text[:self.cursor])
            p = self.padding
            x += p
            h = srf.get_height()
            pygame.draw.line(srf, self.color, (x,p), (x,h-1-p), 2)
        return srf

    def onkeydown(self, ev):
        if ev.mod & (KMOD_CTRL | KMOD_ALT): return
        self.startCursor()
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
        self.startCursor()
        x = self.relXY(ev.pos)[0] - self.padding
        n = len(self.data)
        i = 0
        while i < n and x > self._widthTo(i): i += 1
        self.cursor = i

    def onblur(self, ev):
        if not self.data: self.stale = True
        self.bubble("onaction", ev)
