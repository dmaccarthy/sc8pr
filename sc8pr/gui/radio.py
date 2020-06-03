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


from sc8pr import Canvas, LEFT
from sc8pr.text import Text
from sc8pr.gui.button import Button


class Options(Canvas):
    """GUI control consisting of check boxes and text;
    buttons handle onmousedown; trigger onaction"""

    def __init__(self, text, height=None, padding=4, imgs=None, txtConfig={}):
        text = [Text(t).config(**txtConfig) for t in text]
        check = []
        w = 0
        y = padding
        if not height:
            height = 1 + text[0].height // len(text[0].data.split("\n"))
        for t in text:
            cb = Button.checkbox(imgs).config(height=height)
            yc = y + t.height / 2
            check.append(cb.config(height=height, pos=(padding, yc), anchor=LEFT))
            t.config(pos=(cb.width + 2 * padding, yc), anchor=LEFT, **txtConfig)
            y += t.height + padding
            w1 = cb.width + t.width
            if w1 > w: w = w1
        super().__init__((w + 3 * padding, y))
        self += check + text
        self.boxes = check
        if hasattr(self, "selected"): self.selected = 0


class Radio(Options):
    """GUI control consisting of radio buttons and text;
    buttons handle onmousedown; radio handles onaction and triggers onchange"""

    def __init__(self, text, height=None, padding=4, imgs=None, txtConfig={}):
        if imgs is None: imgs = Button._radioTiles()
        super().__init__(text, height, padding, imgs, txtConfig)

    @property
    def selected(self):
        for cb in self.boxes:
            if cb.selected: return cb

    @selected.setter
    def selected(self, n):
        i = 0
        for cb in self.boxes:
            cb.selected = i == n
            i += 1

    def onaction(self, ev):
        t = ev.target
        if t.enabled:
            change = t.selected
            for cb in self.boxes:
                cb.selected = t is cb
            if change:
#                setattr(ev, "target", self)
                self.bubble("onchange", ev)
    