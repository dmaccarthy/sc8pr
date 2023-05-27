# Copyright 2015-2023 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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


"EXPERIMENTAL -- Scrollable canvas for text buttons"

import os
from fnmatch import fnmatch
from sc8pr import Canvas, TOPLEFT, LEFT, TOPRIGHT
from sc8pr.gui.button import Button, OPTIONS
from sc8pr.gui.slider import Slider
from sc8pr.text import Text, Font
from sc8pr.util import resolvePath

FOLDERS = 1
FILES = 2
SAVE = 3


def fnmatch_any(f, pattern):
    "Match any of the patterns"
    pattern = pattern.split(";")
    f = os.path.split(f)[1]
    for p in pattern:
        if fnmatch(f, p.strip()):
            return True
    return False


class _Button(Button):
    "Customize buttons for TextButtonCanvas"
    allowButton = 1, 4, 5

    @property
    def value(self):
        "Get the button value"
        return getattr(self, "_value", self[0].data)

    @value.setter
    def value(self, v):
        "Set the button value"
        if v is None:
            if hasattr(self, "_value"):
                delattr(self, "_value")
        else:
            self._value = v

    def onclick(self, ev):
        "Handle button click events"
        cv = self.canvas
        if ev.button in (4, 5):
            slider = list(cv.instOf(_Slider))
            if slider:
                slider[0].val += -1 if ev.button == 4 else 1
                slider[0].onchange()
        elif ev.button == 1:
            if self._status < 4:
                if self.selectable:
                    if cv.uniqueSelect:
                        for btn in cv.instOf(_Button):
                            if btn.selected and btn is not self:
                                btn.selected = False
                    self.selected = not self.selected
            ev.targetButton = self
            cv._click(ev)


class _Slider(Slider):
    "Customize slider for TextButtonCanvas"

    reverseWheel = True

    def onchange(self, ev=None):
        "Scroll canvas with slider control"
        self.canvas.scrollTo(round(self.val))


class TextButtonCanvas(Canvas):
    "Canvas subclass for text buttons"
    options = ("#ffffff00", ) + OPTIONS[1:3]
    buttonStyle = dict(weight=0)
    sliderStyle = dict(bg="#f0f0ff")
    knob = None
    uniqueSelect = True
    _lastClick = None

    def __init__(self, size, bg=None):
        "Initialize the instance"
        super().__init__(size, bg=bg)
        self._h = 0

    def _count_overflow(self, dy):
        "Count the number of buttons that do not fit in the canvas"
        btns = list(self.instOf(_Button))
        h = n = 0
        while h < dy:
            n += 1
            h += btns[n].height
        return n

    def scrollTo(self, n=0):
        "Reposition the buttons so button n appears at the top of the canvas"
        y = 0
        hide = self.height + 1
        for btn in self.instOf(_Button):
            if btn.status < 2:
                btn.status = 0
            if n > 0:
                btn.config(pos=(0, hide))
                n -= 1
            else:
                btn.config(pos=(0, y))
                y += btn.height

    def purge(self, recursive=False):
        Canvas.purge(self, recursive)
        self._h = 0
        return self

    def text(self, *args, **kwargs):
        "Add a text button(s)"
        h = self._h
        for text in args:
            t = Text(text).config(**kwargs)
            b = _Button((self.width, t.height), self.options) #.bind(onaction=handle)
            b += t.config(anchor=LEFT, pos=(0, t.height/2))
            self += b.config(anchor=TOPLEFT, pos=(0, h), **self.buttonStyle)
            h += t.height
        self._h = h
        if h > self.height:
            self.removeItems("ScrollBar")
            n = self._count_overflow(h - self.height)
            w, h = self.size
            slider = _Slider((16, h), self.knob, 0, n, n).config(anchor=TOPRIGHT, pos=(w, 0))
            self["ScrollBar"] = slider.config(**self.sliderStyle)
            self.scrollTo()
        return self

    def _click(self, ev):
        btn = ev.targetButton
        sk = self.sketch
        f1 = sk.frameCount
        dbl = False
        if ev.button == 1:
            if self._lastClick:
                btn0, f0 = self._lastClick
                if btn is btn0 and f1 - f0 < sk.frameRate / 2:
                    dbl = True
                    if btn.selectable:
                        btn.selected = True
            self._lastClick = btn, f1
        self.bubble("onaction" if dbl else "onclick", ev)


class FileListCanvas(TextButtonCanvas):
    "File list canvas"
    folderStyle = dict(color="blue")
    _pattern = "*"
    _mode = FOLDERS + FILES
    _folder = None

    def __init__(self, size, bg=None, adjustHeight=False, **kwargs):
        "Initialize the instance"
        self.font = f = dict(font=Font.sans(), fontSize=12, fontStyle=0, padding=2)
        f.update(kwargs)
        if adjustHeight:
            h = Font._get_h(f["font"], f["fontSize"], f["fontStyle"]) + 2 * f["padding"]
            size = size[0], h * round(size[1] / h)
            self.buttonHeight = h
        super().__init__(size, bg=bg)

    @property
    def folder(self):
        "Return the current folder path"
        return self._folder

    def selected(self, mode=2):
        "Return a list of selected folders/files"
        s = []
        for b in self:
            if b.name != "ScrollBar" and b.selected:
                f = resolvePath(b.value, self._folder, True)
                if mode & FOLDERS and os.path.isdir(f) or mode & FILES and os.path.isfile(f):
                    s.append(f)
        return s

    def openFolder(self):
        "Open the selected folder"
        s = self.selected(FOLDERS)
        if s:
            self.showFiles(s[0])
            return True
        else:
            return False

    def showFiles(self, folder=".", pattern=None, mode=None):
        "Create buttons for a set of folders and/or files"
        if pattern is None:
            pattern = self._pattern
        else:
            self._pattern = pattern
        if mode is None:
            mode = self._mode
        else:
            self._mode = mode
        flist = os.listdir(folder)
        self._folder = os.path.abspath(folder)
        a, b = ["[Parent Folder]"], []
        for f in flist:
            full = resolvePath(f, self._folder, True)
            if os.path.isdir(full):
                a.append(f)
            elif fnmatch_any(full, pattern):
                b.append(f)
        flist = a if mode == FOLDERS else b if mode == FILES else (a+b)
        self.purge().text(*flist, **self.font)
        if mode & FOLDERS:
            self[0].value = ".."
            for i in range(len(a)):
                self[i][0].config(**self.folderStyle)
        return self
