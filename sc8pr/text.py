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


import pygame.font as pf
from sc8pr import Renderable, BaseSprite, Image, LEFT, RIGHT
from sc8pr.util import rgba, hasAny, setAlpha, drawBorder

BOLD = 1
ITALIC = 2

fontCacheSize = 32
_fontCache = {}

fontList = sorted(pf.get_fonts())

def findFont(*args):
    "Find an available font from a sequence of font names"
    for f in args:
        f = f.replace(" ", "").lower()
        if f in fontList: return f

MONO = findFont("Inconsolata", "SourceCodePro", "DroidSansMono", "LucidaConsole", "Monaco", "CourierNew", "Courier")
SERIF = findFont("DroidSerif", "Garamond", "Georgia", "TimesNewRoman", "Times")
SANS = findFont("Oxygen", "OpenSans", "DroidSans", "Verdana", "Geneva", "Helvetica", "Arial")

def _makeKey(font, size, style):
    "Normalize the (font, size, style) tuple used as _fontCache key"
    if type(size) is float: size = round(size)
    return font, size, style

def _loadFont(font, size, style=0, cache=True):
    "Load a font into the _fontCache"
    global _fontCache
    key = _makeKey(font, size, style)
    keys = _fontCache.keys()
    if key in keys: return _fontCache[key]
    try: font = pf.Font(*key[:2])
    except: font = pf.SysFont(key[0], key[1], style & 1, style & 2)
    if cache:
        if len(keys) >= fontCacheSize: del _fontCache[tuple(keys)[0]]
        _fontCache[key] = font
    return font


class Text(Renderable):
    font = None
    fontSize = 24
    fontStyle = 0
    bg = None
    color = border = rgba("black")
    weight = 0
    padding = 0
    spacing = 0
    align = LEFT

    def __init__(self, data=""): self.data = data

    def config(self, **kwargs):
        keys = ("data", "color", "bg", "font", "fontSize", "fontStyle",
            "height", "width", "align", "padding", "spacing", "weight",
            "border", "promptColor")
        if hasAny(kwargs, keys): self.stale = True
        for a in kwargs:
            v = kwargs[a]
            if v and a in ("bg", "color", "border", "promptColor"): v = rgba(v)
            setattr(self, a, v)
        return self

    def render(self):
        "Render the text as an Image"
        key = _makeKey(self.font, self.fontSize, self.fontStyle)
        font = _loadFont(*key)
        text = str(self.data).split("\n")
        srfs = [font.render(t, True, self.color) for t in text]
        return self._joinLines(srfs)

    def _joinLines(self, srfs):
        "Join the lines of text into a single surface"

        # Calculate total size
        wMax, hMax = 0, 0
        n = len(srfs)
        for s in srfs:
            w, h = s.get_size()
            if w > wMax: wMax = w
            if h > hMax: hMax = h
        y = self.padding
        w = wMax + 2 * y
        h = n * hMax + (n - 1) * self.spacing + 2 * y

        # Blit lines to final image
        wt = self.weight
        dx = 2 * wt
        y += wt
        srf = Image((w + dx, h + dx), self.bg).image
        a = self.color.a
        for s in srfs:
            if a: s = setAlpha(s, a)
            x = self.padding + wt
            if self.align != LEFT:
                dx = wMax - s.get_size()[0]
                x += dx if self.align == RIGHT else dx // 2
            srf.blit(s, (x, y))
            y += hMax + self.spacing
        if wt: drawBorder(srf, self.border, wt)
        return srf   

    def resize(self, size):
        self.fontSize *= size[1] / self.height
        self.stale = True


class TextSprite(BaseSprite, Text): pass
