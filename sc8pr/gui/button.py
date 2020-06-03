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


from sc8pr import Canvas, Image, LEFT
from sc8pr.text import Text
from sc8pr.util import rgba, sc8prData

OPTIONS = "#e0e0e0", "#b0b0ff", "#8080ff", "#8080ff", "grey"


class Button(Canvas):
    _statusNames = "normal", "hover", "selected", "hoverselected", "disabled"
    _check = None
    _radio = None
    _yesNo = None
    _status = 0
    weight = 1
    allowButton = 1,

    def __init__(self, size=None, options=None):
        self.options = options
        if size is None: size = self._options[0].size
        super().__init__(size)

    def statusName(self, i=None):
        if i is None: i = self._status
        return self._statusNames[i]

    @property
    def status(self): return self._status

    @status.setter
    def status(self, n):
        if type(n) is str: n = self._statusNames.index(n.lower())
        self._status = n

    @staticmethod
    def _checkTiles():
        "Images for creating check boxes"
        if Button._check is None:
            Button._check = Image.fromBytes(sc8prData("checkbox"))
        return Button._check.tiles(5)

    @staticmethod
    def _radioTiles():
        "Images for creating radio check boxes"
        if Button._radio is None:
            Button._radio = Image.fromBytes(sc8prData("radio"))
        return Button._radio.tiles(5)

    @staticmethod
    def checkbox(imgs=None):
        "Return a check box Button"
        if imgs is None: imgs = Button._checkTiles()
        return Button(None, (Image(x) for x in imgs)).config(weight=0)

    @staticmethod
    def radio(): return Button.checkbox(Button._radioTiles())

    @property
    def selectable(self):
        return self._status < 4 and self._options[2] is not None

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

    @property
    def options(self): return self._options

    @options.setter
    def options(self, options):
        "Convert options to a list of colors or images"
        if options is None: options = OPTIONS
        else:
            t = type(options)
            if t is dict:
                options = [options.get(self.statusName(i)) for i in range(5)]
            elif t is int:
                options = [OPTIONS[i] for i in range(options)]
            elif t is not list: options = list(options)
            while len(options) < 5: options.append(None)
        c = lambda x: rgba(x) if type(x) in (str,list,tuple) else x
        options = [c(i) for i in options]
        if options[1] is None: options[1] = options[0] 
        if options[3] is None: options[3] = options[2]
        self._options = options

    def _icon(self, icon, padding):
        h = self.height - 2 * padding
        self += icon.config(height=h)
        w = icon.width
        icon.config(pos=(padding, padding + h / 2), anchor=LEFT)
        return w

    def textIcon(self, text, icon=None, padding=6):
        "Add text and icon to button"
        if type(text) is str: text = Text(text)
        if type(icon) is bool: icon = Image(self._yesNoImg(icon))
        if icon:
            w = self._icon(icon, padding)
            x = (w + padding) / 2
        else: x = w = 0
        cx, cy = self.center
        if cx <= 0:
            self._size = (w + text.width + (3 if w else 2) * padding), self._size[1]
            cx = self.center[0]
        self += text.config(pos=(x + cx, cy))
        return self

    @staticmethod
    def _yesNoImg(n):
        if Button._yesNo is None:
            Button._yesNo = Image.fromBytes(sc8prData("yesNo")).tiles(2)
        return Button._yesNo[0 if n else 1]

    def draw(self, srf=None, mode=3):
        self._bg = self._options[self._status]
        return Canvas.draw(self, srf, mode)

    def snapshot(self):
        self._bg = self._options[self._status]
        return Canvas.snapshot(self)

    def onmouseover(self, ev):
        if self._status < 4: self._status |= 1

    def onmouseout(self, ev):
        if self._status < 4 and ev.target is self:
            self._status &= 254

    def onmousedown(self, ev):
        if self._status < 4 and ev.button in self.allowButton:
            if self.selectable: self.selected = not self.selected
            self.bubble("onaction", ev)
