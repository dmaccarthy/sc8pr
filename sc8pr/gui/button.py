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


from sc8pr import Image, Graphic, Canvas
from sc8pr.util import sc8prData, rgba
from sc8pr.text import Text

_tileCache = {}

def cacheTiles(name, tiles):
    if type(tiles) is int: tiles = tiles, 1
    key = name, tiles
    if key not in _tileCache:
        img = Image.fromBytes(sc8prData(name))
        _tileCache[key] = img.tiles(*tiles)
    return _tileCache[key]


class BaseButton(Graphic):
    "Base class for graphics objects functioning as buttons"
    status = 0

    @property
    def selectable(self): return len(self._img) > 2

    @property
    def selected(self): return bool(self.status & 2)

    @selected.setter
    def selected(self, val):
        self.status = (self.status & 1) + (2 if val else 0)       

    def onmouseover(self, ev):
        self.status = 1 + (self.status & 254)

    def onmouseout(self, ev):
        if ev.target is self:
            self.status = self.status & 254

    def onclick(self, ev):
        if self.selectable: self.selected = not self.selected
        self.bubble("onaction", ev)


class Button(BaseButton):
    """A simple button class with static images for each state:
       [normal, hover, selected, selected+hover]"""

    def __init__(self, images):
        self._img = [Image(i.image) for i in images]
        self._size = images[0].size

    @property
    def image(self):
        "Return the surface for the current button state"
        i = min(self.status, len(self._img) - 1)
        return self._img[i].config(size=self.size).image

    @staticmethod
    def checkbox():
        "Create a checkbox button"
        return Button(cacheTiles("checkbox", (2,2))).config(height=24)


class CanvasButton(Canvas, BaseButton):
    "Class for composing canvases that function as buttons"
    _colors = [rgba(c) for c in ("#ececec", "#c8c8ff", "#a0a0ff", "#b4b4ff")]
    weight = 1

    def __init__(self, size):
        super().__init__(size)
        self.border = "black"

    @property
    def selectable(self): return len(self._colors) > 2

    @property
    def colors(self): return self._colors

    @colors.setter
    def colors(self, colors):
        if type(colors) is int: self._colors = CanvasButton._colors[:colors]
        else: self._colors = [rgba(c) for c in colors]

    def draw(self, srf=None, mode=3):
        i = min(self.status, len(self._colors) - 1)
        self.bg = self._colors[i]
        r = Canvas.draw(self, srf, mode)
        return r
    
    def snapshot(self):
        i = min(self.status, len(self._colors) - 1)
        self.bg = self._colors[i]
        return Canvas.snapshot(self)


class TextButton(CanvasButton):

    def __init__(self, size, text, icon=None, padding=6):
        super().__init__(size)
        w, h = size
        if icon:
            s = h - 2 * padding
            w += s + padding
            self += Image(icon).config(
                size = (s, s),
                pos = (padding, padding),
                anchor = 0
            )
        else: s = 0
        tx = Text(text).config(pos = (w / 2, h / 2))
        self += tx
        tx.layer = 0

    @staticmethod
    def okay(size, text="Okay", padding=6, n=0):
        icon = cacheTiles("yesNo", 2)[n]
        btn = TextButton(size, text, icon, padding).config(colors=2)
        btn[0].config(fontSize=0.4*size[1])
        return btn

    @staticmethod
    def cancel(size, text="Cancel", padding=6):
        return TextButton.okay(size, text, padding, 1)
