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


from sc8pr import Canvas, Image, LEFT
from sc8pr.text import Text
from sc8pr.util import rgba, sc8prData

OPTIONS = "#e0e0e0", "#b0b0ff", "#8080ff", "#8080ff", "grey"
_check = Image.fromBytes(sc8prData("checkbox")).tiles(2, 2)
_radio = Image.fromBytes(sc8prData("radio")).tiles(2, 2)
_yesNo = Image.fromBytes(sc8prData("yesNo")).tiles(2)

def yesNo(which=None):
    if which is True: return Image(_yesNo[0])
    if which is False: return Image(_yesNo[1])
    if which is None: return [Image(_yesNo[i]) for i in (0,1)]


class Button(Canvas):
    _status = 0
    weight = 1

    def __init__(self, size=None, options=None):
        self.makeOptions(options)
        if size is None: size = self.options[0].size
        super().__init__(size)

    def statusName(self, i=None):
        if i is None: i = self._status
        return ("normal", "hover", "selected", "hoverselected", "disabled")[i]

    @staticmethod
    def checkbox(imgs=None):
        "Return a check box Button"
        if imgs is None: imgs = _check
        return Button(imgs[0].size,
            [Image(x) for x in imgs]).config(weight=0)

    @staticmethod
    def radio(): return Button.checkbox(_radio)

    @property
    def selectable(self):
        return self._status < 4 and self.options[2] is not None

    @property
    def selected(self): return self._status in (2, 3)

    @selected.setter
    def selected(self, s):
        if self.selectable:
            if s: self._status |= 2
            else: self._status &= 253

    @property
    def enabled(self): return self._status < 4

    @enabled.setter
    def enabled(self, s=True):
        self._status = 0 if s else 4

    def makeOptions(self, options):
        "Convert options to a list of colors or images"
        if options is None: options = OPTIONS
        else:
            t = type(options)
            if t is dict:
                options = [options.get(self.statusName(i)) for i in range(5)]
            elif t is int:
                options = [OPTIONS[i] for i in range(options)]
            while len(options) < 5: options.append(None)
        c = lambda x: rgba(x) if type(x) in (str,list,tuple) else x
        options = [c(i) for i in options]
        if options[1] is None: options[1] = options[0] 
        if options[3] is None: options[3] = options[2]
        self.options = options

    def content(self, text, icon=None, padding=6, **textCfg):
        x, y = self.center
        if icon:
            h = self.height - 2 * padding
            self += icon.config(height=h, anchor=LEFT,
                pos=(padding, padding + h / 2))
            x += (icon.width + padding) / 2
        if not isinstance(text, Text): text = Text(text)
        self += text.config(pos=(x,y)).config(**textCfg)
        return self

    def draw(self, srf=None, mode=3):
        self._bg = self.options[self._status]
        return Canvas.draw(self, srf, mode)

    def snapshot(self):
        self._bg = self.options[self._status]
        return Canvas.snapshot(self)

    def onmouseover(self, ev):
        if self._status < 4: self._status |= 1

    def onmouseout(self, ev):
        if self._status < 4 and ev.target is self:
            self._status &= 254

    def onclick(self, ev):
        if self.selectable: self.selected = not self.selected
        self.bubble("onaction", ev)
