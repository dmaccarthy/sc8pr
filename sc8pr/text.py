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


from sys import stderr
import pygame.font as pf
from sc8pr import Renderable, Image, LEFT, RIGHT, BaseSprite
from sc8pr.util import rgba, hasAny, setAlpha, drawBorder

BOLD = 1
ITALIC = 2


class Font:
    log = True
    cacheSize = 32
    _sort = None
    _cache = {}
    _cacheOrder = []
    _serif = ("Merriweather", "DroidSerif", "Deja Vu Serif", "Palatino",
        "Garamond", "Georgia", "Century", "TimesNewRoman", "Times")
    _sans = ("MerriweatherSans", "OpenSans", "Arsenal", "Oxygen",
        "DroidSans", "Deja Vu Sans", "LucidaSans", "Verdana", "Geneva", "Helvetica", "Arial")
    _mono = ("SourceCodePro", "Inconsolata", "LucidaConsole",
        "DroidSansMono", "Deja Vu Sans Mono", "Monaco", "CourierNew", "Courier")

    @staticmethod
    def _key(name, size=24, style=0):
        if name and "." not in name:
            name = name.replace(" ", "").lower()
        size = round(size)
        return name, size, style

    @classmethod
    def dumpCache(cls): cls._cache.clear()

    @classmethod
    def get(cls, name, size=24, style=0):
        if name and type(name) is not str: name = cls.find(*name)
        key = cls._key(name, size, style)
        cache = cls._cache
        if key in cache:
            font = cache[key]
        else:
            font = cls._get(*key)
            cache[key] = font
            order = cls._cacheOrder
            order.append(key)
            if len(cache) > cls.cacheSize:
                if cls.log: print("sc8pr.text.Font cache is full! Deleting",
                    order[0], file=stderr)
                del cache[order[0]]
                cls._cacheOrder = order[1:]
        return font

    @classmethod
    def _get(cls, name, size, style):
        if name and "." in name:
            font = pf.Font(name, size)
        else:
            font = pf.SysFont(name, size, style & 1, style & 2)
        return font
    
    @classmethod
    def installed(cls):
        if not cls._sort: cls._sort = sorted(pf.get_fonts())
        return cls._sort

    @classmethod
    def find(cls, *args):
        for f in args:
            f = cls._key(f)[0]
            if f == "mono": f = Font.mono()
            elif f == "sans": f = Font.sans()
            elif f == "serif": f = Font.serif()
            if f in Font.installed(): return f

    @staticmethod
    def mono(): return Font.find(*Font._mono)

    @staticmethod
    def sans(): return Font.find(*Font._sans)

    @staticmethod
    def serif(): return Font.find(*Font._serif)


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

    def __iadd__(self, v):
        self.data += v
        self.stale = True
        return self

    def config(self, **kwargs):
        keys = ("bg", "color", "border", "promptColor", "data",
            "font", "fontSize", "fontStyle", "height", "width",
            "align", "padding", "spacing", "weight")
        if hasAny(kwargs, keys): self.stale = True
        for a in kwargs:
            v = kwargs[a]
            if v and a in keys[:4]: v = rgba(v)
            setattr(self, a, v)
        return self

    def render(self):
        "Render the text as an Image"
        font = Font.get(self.font, self.fontSize, self.fontStyle)
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
            if a < 255: setAlpha(s, a)
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


class TextSprite(Text, BaseSprite): pass
