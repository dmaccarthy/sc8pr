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


from sc8pr import Canvas, TOPLEFT
from sc8pr.gui.button import Button


class Menu(Canvas):
    "Class for composing menus"

# Usage example...

# items = [("Open", "Ctrl+O", Image("open.png")), ("Save", "Ctrl+S"), "Exit"]
# menu = Menu(items, txtConfig={"fontSize":14})

    def __init__(self, buttons, size=(192,24),
            options=2, weight=1, padding=6, txtConfig={}):
        isInt = type(buttons) is int
        if isInt or isinstance(buttons[0], Button): items = None
        else:
            items = buttons
            buttons = len(items)
            isInt = True
        if isInt:
            buttons = [Button(size, options) for i in range(buttons)]
        w, h = buttons[0].size
        y = weight
        for btn in buttons:
            btn.config(anchor=TOPLEFT, pos=(weight, y))
            y += h
        w += 2 * weight
        h = len(buttons) * h + 2 * weight
        super().__init__((w, h), btn.options[0])
        self += buttons
        self.config(weight=weight)
        if items: self.items(items, padding, txtConfig)

    def items(self, data, padding=6, textCfg={}):
        "Add text and icons to the menu buttons"
        i = 0
        for item in data:
            if type(item) is str: item = item,
            n = len(item)
            right = item[1] if n > 1 else None
            icon = item[2] if n > 2 else 0
            self[i].menuItem(item[0], right, icon, padding, textCfg)
            i += 1
        return self

    def buttonNumber(self, target):
        "Return the layer (index) of the button containing the target graphic"
        btn = target.canvas
        if btn is self: btn = target
        return btn.layer
