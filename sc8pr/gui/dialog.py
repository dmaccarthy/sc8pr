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
from sc8pr import Canvas, BOTTOM, TOP
from sc8pr.text import Text, Font, BOLD
from sc8pr.gui.button import Button
from sc8pr.gui.textinput import TextInputCanvas
from sc8pr.util import ondrag
import sc8pr.gui.tk as tk


class Dialog(Canvas):

    def insertTop(self, gr, padding=12, name=None):
        "Insert content at top of dialog"
        try: tb = self["TitleBar"],
        except: tb = ()
        self.shiftContents((0, gr.height + padding), *tb)
        y = padding + (tb[0].height if tb else 0) # + self.weight
        gr.config(anchor=TOP, pos=(self.center[0], y))
        gr.setCanvas(self, name)
        return self

    def title(self, title, padding=4, **kwargs):
        "Add a title bar"
        txtConfig = dict(font=Font.sans(), fontSize=15,
            fontStyle=BOLD, color="white", padding=padding)
        txtConfig.update(kwargs)
        title = Text(title).config(**txtConfig)
        cv = Canvas((self.width, title.height + self.weight), self.border)
        cv += title.config(pos=(cv.center[0], self.weight), anchor=TOP)
        self.insertTop(cv, 0, "TitleBar")
        return self

    def resize(self, size): pass


class MessageBox(Dialog):
    "Create simple GUI dialogs"

    def __init__(self, text, userInput=None, buttons=None, title=None, size=(1,1), inputWidth=None, **kwargs):
        super().__init__(size)
        self.command = None

        # Text options
        txtConfig = {"font":Font.sans(), "fontSize":15}
        txtConfig.update(kwargs)

        # Compose button text
        if buttons is None:
            buttons = ["Okay", "Cancel"]
        elif type(buttons) is str: buttons = buttons,
        if len(buttons) > 2: buttons = buttons[:2]

        # Add buttons
        bSize = None
        icon = True
        for t in buttons:
            t = Text(t).config(**txtConfig)
            if not bSize: bSize = 0, t.height + 12
            name = "Button_{}".format(t.data)
            self[name] = Button(bSize, 2).textIcon(t, icon).config(anchor=BOTTOM)
            icon = not icon
        self.buttons = self[:len(buttons)]
        for b in self.buttons: b.bind(onaction=_btnClick)

        # Add text label and text input
        self["Text"] = text = Text(text).config(anchor=TOP, **txtConfig)
        if userInput is None and isinstance(self, NumInputBox):
            userInput = ""
        if userInput is not None:
            if inputWidth and inputWidth < text.width:
                inputWidth = text.width
            self["Input"] = TextInputCanvas(inputWidth, userInput,
                "Click to enter your response", **txtConfig).config(anchor=TOP,
                bg="white")
            self["Input"].ti.config(blurAction=False, mb=self).bind(onaction=_tiAction)

        # Position controls and add title bar
        self._arrange().config(bg="#f0f0f0", weight=2, border="blue")
        if title: self.title(title, **txtConfig)

    def _arrange(self, padding=12):
        "Adjust size and position of controls"

        # Get references to controls
        try: ti = self["Input"]
        except: ti = None
        btns = self.buttons
        text = self["Text"]

        # Calculate button width and position button text
        w = max(b.width for b in btns)
        for b in btns:
            t = b[-1]
            pos = t.pos[0] + (w - b.width) / 2, t.pos[1]
            t.config(pos=pos)
            b._size = w, self[0].height

        # Calculate dialog dimensions
        w = len(btns) * (w + padding) - padding
        w = max(w, text.width, ti.width if ti else 0) + 2 * padding
        h = btns[0].height + text.height + 3 * padding
        if ti: h += ti.height + padding
        y = max(h, self._size[1])
        self._size = max(w, self._size[0]), y
        
        # Position text label and text input
        x = self.center[0]
        text.config(pos=(x, padding))
        if ti: ti.config(pos=(x, text.height + 2 * padding))

        # Position buttons
        if len(btns) > 1: x -= (btns[0].width + padding) / 2
        y -= padding
        for b in btns:
            b.config(pos=(x,y))
            x = self._size[0] - x
        return self

    @property
    def data(self):
        "Get the data from the text input"
        try: ti = self["Input"].ti.data
        except: ti = None
        return ti

    @property
    def result(self):
        cmd = self.command
        btn = self.buttons
        if len(btn) > 1 and cmd == btn[1]: # Cancel button
            return False
        if cmd is None or not self.valid: # Not finished
            return None
        return True if self.data is None else self.data

    @property
    def valid(self): return True

    def onaction(self, ev):
        "Remove dialog when dismissed"
        if self.result is None:
            self.command = None
        else:
            self.remove().canvas.bubble("onaction", ev)

    def ondrag(self, ev):
        ti = "Input" in self and self["Input"] in ev.hover.path
        if not ti: ondrag(self, ev)


class NumInputBox(MessageBox):

    @property
    def data(self):
        try: ti = float(self["Input"].ti.data)
        except: ti = None
        return ti

    @property
    def valid(self):
        return self.data is not None


def _btnClick(gr, ev):
    "Event handler for button clicks"
    _attemptSubmit(gr.canvas, gr, ev)

def _tiAction(gr, ev):
    "Event handler for text input action"
    _attemptSubmit(gr.mb, gr, ev)

def _attemptSubmit(mb, gr, ev):
    mb.command = gr
    if mb.result is not None: mb.bubble("onaction", ev)
    else: mb.command = None

def ask(dialog, allowQuit=True, **kwargs):
    "Run a tkinter dialog"
    tk.init()
    if allowQuit is not None: pygame.event.set_blocked(pygame.QUIT)
    val = dialog(**kwargs)
    if allowQuit: pygame.event.set_allowed(pygame.QUIT)
    return val
