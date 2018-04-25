# Copyright 2015-2018 D.G. MacCarthy <http://dmaccarthy.github.io>
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


from sc8pr import Canvas, TOPLEFT, LEFT, RIGHT, Image
from sc8pr.gui.button import Button
from sc8pr.text import Text
import pygame

R_TRIANGLE = 1


class Menu(Canvas):
    "Class for composing menus"
    _tri = None

    def __init__(self, items, size=(192,24), weight=1, padding=6, options=2, txtConfig={}):
        w, h = size
        x = y = weight
        if "fontSize" not in txtConfig:
            tmp = dict(fontSize=h-padding)
            tmp.update(txtConfig)
            txtConfig = tmp
        if type(items) is int:
            n = items
            items = None
        else: n = len(items)
        buttons = []
        for i in range(n):
            b = Button(size, options).config(anchor=TOPLEFT, pos=(x,y), weight=0)
            buttons.append(b)
            y += h
            if items:
                self._item(b, items[i], padding)
                for gr in b:
                    if isinstance(gr, Text): gr.config(**txtConfig)
        w += 2 * weight
        h = n * size[1] + 2 * weight
        super().__init__((w,h), buttons[0].options[0])
        self.config(weight=weight)
        self += buttons

    @staticmethod
    def _item(btn, data, padding):
        h = btn.height - 2 * padding
        y = padding + h / 2
        x = h + padding * (2 if h else 1)
        if type(data) is str: data = data, None, None
        text, left, right = [Text(d) if type(d) is str else d for d in data]
        if text: btn += text.config(anchor=LEFT, pos=(x,y))
        if left: btn += left.config(pos=(y,y), height=h)
        x = btn.width - padding
        if right:
            if right == R_TRIANGLE: right = Menu.triangle()
            btn += right.config(anchor=RIGHT, pos=(x,y), height=h)

    @staticmethod
    def triangle():
        if Menu._tri is None:
            srf = Image((56,64)).image
            pygame.draw.polygon(srf, (0,0,0), [(0,8), (0,56), (55,32)])
            Menu._tri = srf
        return Image(Menu._tri)

    def buttonNumber(self, target):
        "Return the layer (index) of the button containing the target graphic"
        return target.pathTo(self)[-2].layer
