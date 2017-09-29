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


from sc8pr import Canvas, LEFT
from sc8pr.text import Text
from sc8pr.gui.button import Button


class Radio(Canvas):

    def __init__(self, text, space=4, **kwargs):
        text = [Text(t).config(**kwargs) for t in text]
        check = []
        y = w = 0
        h = kwargs["fontSize"] if "fontSize" in kwargs else Text.fontSize
        for t in text:
            cb = Button.checkbox()
            h = max(t.height, cb.height)
            yc = y + h / 2
            check.append(cb.config(height=h, pos=(0, yc), anchor=LEFT))
            t.config(pos=(cb.width + space, yc), anchor=LEFT, **kwargs)
            y += h + space
            w1 = cb.width + t.width
            if w1 > w: w = w1
        super().__init__((w + space, y - space))
        self += check + text
        self.boxes = check
        check[0].selected = True

    @property
    def selected(self):
        for cb in self.boxes:
            if cb.selected: return cb

    def onaction(self, ev):
        change = not ev.target.selected
        for cb in self.boxes:
            cb.selected = cb is ev.target
        if change:
            setattr(ev, "target", self)
            self.bubble("onchange", ev)
