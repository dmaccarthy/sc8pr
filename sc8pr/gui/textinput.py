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


import pygame
from pygame.constants import KEYDOWN, K_ESCAPE, K_BACKSPACE, K_LEFT, K_RIGHT,\
    K_DELETE, K_HOME, K_END, KMOD_CTRL, KMOD_ALT, KMOD_SHIFT, K_LSHIFT, K_RSHIFT
from sc8pr import Canvas, LEFT, CENTER, TOP
from sc8pr.text import Text, Font
from sc8pr.util import style, rgba
from sc8pr.geom import vec2d, sigma
from sc8pr.gui.tk import clipboardGet, clipboardPut


_ANGLE_ERROR = "Operation is only supported for angles of 0 or 90"


class TextInput(Text):
    """Editable text GUI control:
    handles ondraw, onmousedown, ondrag, onkeydown, onblur;
    triggers onchange, onaction"""
    focusable = True
    cursorTime = 1.0
    cursorOn = 0.35
    promptColor = rgba("#d0d0d0")
    padding = 4
    allowButton = 1,
    blurAction = True
    _cursorX = 0
    _scrollX = 0
    _selection = None
    _highlight = None
    _submit = False

    def __init__(self, data="", prompt=None):
        super().__init__(str(data).split("\n")[0])
        self.cursor = len(self.data)
        self.cursorStatus = False
        self.prompt = prompt

    @property
    def highlight(self):
        if self._highlight: return self._highlight
        c = self.color
        return pygame.Color(c.r, c.g, c.b, 48)

    @highlight.setter
    def highlight(self, c): self._highlight = rgba(c)

    def _startCursor(self):
        self.stale = True
        self.cursorStatus = True
        self.cursorStart = self.sketch.frameCount

    def draw(self, srf):
        if self.focussed:
            sk = self.sketch
            try: n = (sk.frameCount - self.cursorStart) / sk.frameRate
            except: n = None
            if n is None or n > self.cursorTime: self._startCursor()
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
        prompt = self.prompt and not self.data and not focus
        if prompt:
            color = self.promptColor
            text = self.prompt
        else:
            color = self.color
            text = self.data
        try: srf = font.render(text, True, color)
        except:
            text = "[Unable to render!]"
            srf = font.render(text, True, color)
            if prompt: self.prompt = text
            else:
                self.data = text
                self.cursor = 0
        srf = style(srf, self.bg, self.border, self.weight, self.padding)

        # Highlight selection and draw cursor
        c = self.cursor
        if self.data:
            p0 = text[c-1:c] if c else text[0]
            p1 = text[c:c+1] if c < len(self.data) else text[-1]
            self._scrollPad = [font.size(p)[0] for p in (p0, p1)]
        else:
            self._scrollPad = 0, 0
        x = font.size(text[:c])[0]
        p = self.padding
        x += p
        self._cursorX = x
        h = srf.get_height()
        s = self._selection
        if s not in (None, self.cursor):
            x0 = font.size(text[:s])[0] + p
            w = abs(x - x0)
            s = pygame.Surface((w, h - 2 * p), pygame.SRCALPHA)
            s.fill(self.highlight)
            srf.blit(s, (min(x, x0), p))
        if self.cursorStatus:
            pygame.draw.line(srf, self.color, (x,p), (x,h-1-p), 2)
        return srf

    def _paste(self, data):
        "Paste the clipboard contents at the cursor location"
        clip = clipboardGet()
        if clip:
            for c in "\n\r\t": clip = clip.replace(c, "")
            c = self.cursor
            data = data[:c] + clip + data[c:]
            self.config(data=data)
            self.cursor += len(clip)
            return True

    def _selectRange(self):
        c = self.cursor
        s = self._selection
        if s is None: s = c
        else:
            tmp = max(s, c)
            c = min(s, c)
            s = tmp
        return c, s
        
    def deleteSelection(self):
        c, s = self._selectRange()
        if c == s: return False
        self.stale = True
        self.data = self.data[:c] + self.data[s:]
        self._selection = None
        self.cursor = c
        return True

    def onkeydown(self, ev):

        # Process 'submit' action
        u = ev.unicode
        if u in ("\n", "\r"): #, "\t"):
            self._submit = True
            self.blur(True)
            self._submit = False
            return

        # Ignore keys with Ctrl or Alt modifier (except Ctrl+[ACVX])
        k = ev.key
        acvx = [ord(c) for c in "acvxACVX"]
        if (ev.mod & KMOD_ALT or (ev.mod & KMOD_CTRL and k not in acvx)):
            return

        # Mark rendering as stale
        self.stale = True
        self._startCursor()
        cursor = self.cursor
        data = self.data
        n = len(data)

        # Process Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X
        if ev.mod & KMOD_CTRL:
            acvx = acvx.index(k) % 4
            if acvx % 2:
                c, s =  self._selectRange()
                if c != s: clipboardPut(data[c:s])
            if acvx == 0:
                self._selection = 0
                self.cursor = n
            elif acvx > 1:
                change = self.deleteSelection()
                if acvx == 2:
                    if self._paste(self.data): change = True
                if change: self.bubble("onchange", ev)
            return

        # Arrow keys
        if k in (K_LEFT, K_RIGHT, K_HOME, K_END):
            if ev.mod & KMOD_SHIFT:
                if self._selection is None: self._selection = cursor
            else: self._selection = None
            if cursor:
                if k == K_LEFT: cursor -= 1
                elif k == K_HOME: cursor = 0
            if cursor < n:
                if k == K_RIGHT: cursor += 1
                elif k == K_END: cursor = n
            self.cursor = cursor
            return

        # Backspace and delete
        if k in (K_BACKSPACE, K_DELETE):
            if self.deleteSelection(): cursor = self.cursor
            elif cursor and k == K_BACKSPACE:
                self.data = data[:cursor-1] + data[cursor:]
                cursor -= 1
            elif cursor < n and k == K_DELETE:
                self.data = data[:cursor] + data[cursor+1:]

        # Character keys
        if k >= 32 and k < 127:
            if self.deleteSelection():
                cursor = self.cursor
                data = self.data
            self.data = data[:cursor] + u + data[cursor:]
            cursor += 1

        # Finish up
        self.cursor = cursor
        if self.data != data:
            self._selection = None
            self.bubble("onchange", ev)

    def _widthTo(self, i):
        font = Font.get(self.font, self.fontSize, self.fontStyle)
        d = self.data
        return (font.size(d[:i])[0] + font.size(d[:i+1])[0]) // 2

    def onmousedown(self, ev):
        drag = ev.handler == "ondrag" 
        if drag or ev.button in self.allowButton:
            self._startCursor()
            x = self.relXY(ev.pos)[0] - self.padding
            n = len(self.data)
            i = 0
            while i < n and x > self._widthTo(i): i += 1
            k = self.sketch.key
            if drag or k and k.type == KEYDOWN and k.key in (K_LSHIFT, K_RSHIFT):
                if self._selection is None:
                    self._selection = self.cursor
            else: self._selection = None
            self.cursor = i
            self.stale = True
        elif not hasattr(self, "cursorStart"): self.blur()

    ondrag = onmousedown

    def onblur(self, ev):
        self._selection = None
        if not self.data: self.stale = True
        if hasattr(self, "cursorStart"): del self.cursorStart
        cv = self.canvas
        if (self._submit or self.blurAction) and not (ev.focus is cv and isinstance(cv, TextInputCanvas) and cv.ti is self):
            self.bubble("onaction", ev)

    def _scrollCalc(self, a):
        """Calculate how many pixels to scroll to keep the
           text insertion point visible within the canvas"""
        if a not in (0, 90): raise ValueError(_ANGLE_ERROR)
        if a: a = 1
        cv = self.canvas
        width = cv.size[a]
        if self.width < width: return 0, False
        pad = self.padding
        x = self.rect.topleft[a] + self._cursorX - cv.rect.topleft[a]
        p0, p1 = self._scrollPad
        c = self.cursor
        if c == 0: p0 = 0
        if c == len(self.data): p1 = 0
        if x < pad + p0: pix = pad + p0 - x
        else:
            pad += p1
            width -= pad + 1
            if x > width: pix = width - x
            else: pix = 0
        return pix, True

    def scroll(self, pix=None, rel=True):
        # Calculate scroll when not specified
        a = self.angle
        if pix is None: pix = self.focussed and a in (0, 90)
        if pix is False: pix, rel = 0, False
        elif pix is True: pix, rel = self._scrollCalc(a)

        # Set scrolling attributes
        if pix or not rel:
            if rel: self._scrollX += pix
            else:
                tmp = pix
                pix -= self._scrollX
                self._scrollX = tmp
            if pix:
                if a == 90: self.pos = self.pos[0], self.pos[1] + pix
                else: self.pos = sigma(self.pos, vec2d(pix, a))
        return self

    ondraw = scroll


class TextInputCanvas(Canvas):
    "Create a text input inside a canvas"

    focusable = True

    def __init__(self, width=None, data="", prompt=None, center=False, vertical=False, **text):
        ti = self._ti(vertical, data, prompt, **text)
        super().__init__((width if width else ti.width, ti.height))
        cfg = {"anchor":CENTER, "pos":self.center} if center \
            else {"anchor":TOP, "pos":(self.center[0], 0)} if vertical \
            else {"anchor":LEFT, "pos":(0, self.center[1])}
        self.ti = ti.config(**cfg)
        self += ti

    def _ti(self, v, data, prompt=None, **text):
        ti = data if isinstance(data, TextInput) else TextInput(data, prompt).config(**text)
        return ti.config(angle=90 if v else 0)

    @property
    def data(self): return self.ti.data

    @data.setter
    def data(self, data): self.ti.config(data=data)

    def onmousedown(self, ev): self.ti.focus().onmousedown(ev)


clipboardGet()
