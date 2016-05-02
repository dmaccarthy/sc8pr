# Copyright 2015-2016 D.G. MacCarthy <devwigs@gmail.com>
#
# This file is part of WIGS.
#
# WIGS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# WIGS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with WIGS.  If not, see <http://www.gnu.org/licenses/>.


"Simplified GUI input and output"

import pygame
from wigs.widgets import Widget, MsgBox, Container
from wigs.grid import FileDialog

USERINPUT = pygame.USEREVENT + 1
_error = RuntimeError("A dialog is already running!")
_name = "UserInput"
_font = "sans"
_size = 13
number = MsgBox.number


class SimpleFileDialog(FileDialog):
    "A class for creating simple file system dialogs from within a sketch"
    
    def __init__(self, mode, allowCancel, initFilter):
        super().__init__(mode, allowCancel=allowCancel, initFilter=initFilter)

    def _onEvent(self, ev):
        if ev.type in (ev.CANCEL, ev.SUBMIT):
            self.sketch.io = None
            val = None if ev.type == ev.CANCEL else ev.value
            return pygame.event.Event(USERINPUT, name=_name, value=val)


def fileDialog(sk, mode=0, allowCancel=True, initFilter="*.*"):
    "Place a SimpleFileDialog instance and encapsulate it in the sketch"
    if not Container.font: Container.font = sk.loadFont(_font, _size + 2, True, lineHeight=False)
    if not Widget.font: Widget.font = sk.loadFont(_font, _size, lineHeight=False)
    if sk.io: raise(_error)
    sk.io = SimpleFileDialog(mode, allowCancel, initFilter)
    sk.gui.place(sk.io)
    return sk.io


class SimplePrompt(MsgBox):
    "A class for creating simple user I/O message boxes from within a sketch"

    def __init__(self, msg, title, validator, default, minSize, **kwargs):
        if validator is bool:
            btns = "Yes", "No"
            validator = None
            if not title: title = "Confirm..."
        else:
            btns = None
            if not title: title = "Prompt..." if validator else "Alert..."
        super().__init__(msg, btns, title=title, validator=validator, default=default, minSize=minSize, **kwargs)

    def _onEvent(self, ev):
        if ev.type in (ev.CANCEL, ev.SUBMIT):
            self.sketch.io = None
            if ev.type == ev.CANCEL: return pygame.event.Event(USERINPUT, name=_name, value=None)
            else:
                if self.validator: val = ev.value
                else:
                    val = self.buttonNames[ev.target.index] == "Yes" if len(self.buttons) > 1 else None
                return pygame.event.Event(USERINPUT, name=_name, value=val)


def prompt(sk, msg, validator=str, default="", title=None, minSize=(144,1), **kwargs):
    "Place a Prompt instance and encapsulate it in the sketch"
    assert sk.gui, "GUI manager has not been initialized"
    if not Container.font: Container.font = sk.loadFont(_font, _size + 2, True, lineHeight=False)
    if not Widget.font: Widget.font = sk.loadFont(_font, _size, lineHeight=False)
    if sk.io: raise(_error)
    sk.io = SimplePrompt(msg, title, validator, default, minSize, **kwargs)
    sk.gui.place(sk.io)
    if sk.io.input: sk.gui.focus = sk.io.input
    return sk.io
