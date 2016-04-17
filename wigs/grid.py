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


import pygame, os, fnmatch, json
from wigs.widgets import Button, Slider, MsgBox, TextInput, Label
from wigs.gui import Widget, Container, GuiEvent
from wigs.image import Image
from wigs.util import fontHeight, isEnter, containsAny, wigsPath


# FileDialog modes...
OPEN = 0
SAVE = 1
FOLDER = 2


class ButtonGrid(Container):
    space = 0
    buttonSize = 1, 1

    def __init__(self, grid, vertical=False, name=None, posn=(0,0), **kwargs):
        self.cols, self.rows = grid
        self.vertical = vertical
        self.setStyle(**kwargs)
        super().__init__(name, posn)

    def getSize(self, reset=True):
        w, h = self.buttonSize
        e = 2 * (self.border + self.space)
        return self.cols * w + e, self.rows * h + e

    def startAt(self, n):
        w, h = self.buttonSize
        w += self.space
        h += self.space
        i = 0
        self.start = n
        for wdg in self:
            if self.vertical:
                r = (i - n) // self.cols
                c = (i - n) % self.cols
            else:
                c = (i - n) // self.rows
                r = (i - n) % self.rows
            wdg.visible = r >= 0 and c >= 0 and r < self.rows and c < self.cols
            wdg.posn = (c*w, r*h) if wdg.visible else (0,0)
            i += 1


class FileBrowser(Container):
    """A Widget for navigating the file system"""

    border = 1
    borderColor = altBdColor = Widget.borderColor
    cwd = "."
    iconPath = wigsPath("icons/{}.png")
    iconJson = wigsPath("icons/fileBrowser.json")
    groups = {}

    def __init__(self, items=".", grid=(3,10), name=None, posn=(0,0), itemFilter=None, **kwargs):
        self.setStyle(**kwargs)
        border = self.border
        super().__init__(name, posn, None, border=0)
        self.loadIconMap()
        self.filter = itemFilter
        self.grid = g = ButtonGrid(grid, True, border=border, bgColor=FileItem.colors[0], altBdColor=self.altBdColor, borderColor=self.borderColor)
        g.focusable = True
        g.space = -FileItem.border
        if type(items) == str: items = self.listdir(items)
        self.metric = m = FileItem.metrics()
        g.buttonSize = m[3]
        self.slider = s = Slider((0,), (m[0][1] + 2 * border, g.getHeight()), step=1,
                posn=g.beside(0), border=border, borderColor=self.borderColor, swap=True)
        s.x -= border
        self.place(g, s)
        self.draw(items)

    @classmethod
    def imageFile(cls, name): return cls.iconPath.format(name)

    @classmethod
    def loadIconMap(cls):
        try:
            with open(cls.iconJson) as f:
                cls.iconMap, FileBrowser.groups = json.load(f)
                for i in cls.iconMap:
                    cls.iconMap[i] = [None, cls.iconMap[i]]
        except: cls.iconMap = {"file":[None, []]}

    def getIcon(self, item):
        sz = self.metric[0]
        if item == "..": ext = item
        else:
            ext = item.split(".")[-1].lower() if "." in item else ""
            item = self.cwd + "/" + item
            if os.path.isdir(item): ext = True
        for img in self.iconMap:
            imap = self.iconMap[img] 
            exts = imap[1]
            if ext in exts:
                if imap[0] == None:
                    try: icon = Image(self.imageFile(img))
                    except: icon = Image.text("?", font=self.font)
                    imap[0] = icon
                return imap[0].fit(sz)
        img = self.iconMap["file"][0]
        if img == None: self.iconMap["file"][0] = img = Image(self.imageFile("file")).fit(sz)
        return img

    def listdir(self, path=".", fail="."):
        path = self.abspath(path)
        try: items = os.listdir(path)
        except: return self.listdir(fail)
        self.cwd = path
        fldr = sorted([f for f in items if os.path.isdir(self.cwd + "/" + f)], key=str.lower)
        if ".." not in fldr: fldr = [".."] + fldr
        file = [f for f in items if os.path.isfile(self.cwd + "/" + f)]
        return self.filter[0](fldr, file, self.filter[1]) if self.filter else (fldr + file)

    def getSelected(self): return self.grid.widgets[0].getSelected()

    @property
    def selectedPath(self):
        btn = self.getSelected()
        return os.path.abspath(self.cwd.replace("\\","/") + "/" + btn.name) if btn else None

    @property
    def filterText(self): return self.filter[1]

    @filterText.setter
    def filterText(self, txt):
        self.filter = self.filter[0], txt
        self.open(".")

    def draw(self, items, start=0):
        g, s = self.grid, self.slider
        g.empty()
        for item in items:
            up = item == ".."
            text = "Parent Folder" if up else item
            g.place(FileItem(text, self.getIcon(item), name=item, color=(0,0,255) if up else (0,0,0)))
        w = g.widgets[0]
        w.makeGroup(*g.widgets)
        w.selected = False
        sRow = start // g.cols
        g.startAt(g.cols * sRow)
        r = 1 + (len(items) - 1) // g.cols
        if r <= g.rows:
            s.config((0,), handle=0)
        else:
            s.config((0, r-g.rows), handle=g.rows)
        s.value = r - sRow

    def abspath(self, path):
        cwd = os.getcwd()
        try:
            os.chdir(self.cwd)
            path = os.path.abspath(path)
        except: path = "."
        finally: os.chdir(cwd)
        return path
    
    def open(self, path): self.draw(self.listdir(path))

    def _event(self, ev):
        g, s = self.grid, self.slider
        if ev.target is s:
            g.startAt(g.cols * (s.max - s.value))
        elif ev.type == GuiEvent.DBL_CLICK and self.cwd and isinstance(ev.target, FileItem):
            ev = self.submit(ev)
        return self._onEvent(ev)

    def submit(self, ev):
        s = self.grid.widgets[0].getSelected()
        path = os.path.abspath(self.cwd + "/" + s.name).replace("\\", "/")
        ev.folder = os.path.isdir(path)
        if ev.folder:
            self.grid.empty() #widgets = []
            self.open(path)
            ev.target = self
        return ev

    @staticmethod
    def folders(fldr, file, args): return fldr

    @staticmethod
    def match(fldr, file, args):
        fltr = []
        args = args.lower()
        for a in FileBrowser.groups:
            args = args.replace(a, FileBrowser.groups[a])
        for a in args.lower().split(";"):
            if len(a) > 1 and a[0] == "<":
                key = a[1:].split(">")[0]
                imap = FileBrowser.iconMap
                imap = imap[key][1] if key in imap else []
                for t in imap: fltr.append("*." + t)
            else: fltr.append(a)
        match = []
        for a in fltr:
            match.extend(fnmatch.filter(file, a))
        return fldr + sorted(set(match), key=str.lower)


class FileDialog(Container):
    pad = 8
    border = 3
    bgColor = MsgBox.bgColor
    modal = True

    def __init__(self, mode=OPEN, grid=(2,10), allowClose=True, allowCancel=True, title=None, initFilter="*.*"):
        if not title: title = ("Open File", "Save As", "Select Folder")[mode] + "..."
        super().__init__(title=title, posn="C")
        self._cwd = None
        self.mode = mode
        self.grid = grid
        self.allowClose = allowClose
        self.allowCancel = allowCancel
        self.initFilter = "<Folder>" if mode == FOLDER else initFilter
        self.layout()

    def layout(self):
        # FileBrowser grid and location TextInput...
        fn = FileBrowser.folders if self.mode == FOLDER else FileBrowser.match
        self.browser = FileBrowser(grid=self.grid, itemFilter=(fn, self.initFilter))
        w = self.browser.getWidth() - 2 * (TextInput.pad + 1)
        self.putCwd()
        self.browser.posn = self._cwd.below(self.pad)
        self.place(self.browser)

        # Buttons and filter...
        btn = Button.grid((("Open", "Save", "Select")[self.mode], "Cancel"))
        self.done, self.cancel = btn.widgets
        if not self.allowCancel: self.cancel.disable()
        btn.posn = self.browser.below(self.pad, "E", btn.getWidth())
        x = w - btn.getWidth() - fontHeight(Button) // 2
        self._filter = TextInput(txt=self.filter, inner=(x, None), posn=(0, btn.posn[1]))
        self.place(btn, self._filter)

    @property
    def cwd(self): return self.browser.cwd

    def putCwd(self):
        bw = self.browser.getWidth()
        if self._cwd: self._cwd.remove()
        self._cwd = Label(self.cwd, color=self.borderColor, font=FileItem.font)
        w, h = self._cwd.getSize()
        self._cwd.crop((bw, h), "E" if w > bw else "W")
        self.place(self._cwd)

    @property
    def filter(self): return self.browser.filterText

    @filter.setter
    def filter(self, val):
        path = self.browser.abspath(val).replace("\\", "/")
        if os.path.isdir(path):
            fltr = None
        elif "/" in path:
            fltr = path.split("/")[-1]
            n = len(path) - len(fltr)
            path = path[:n]
            if len(fltr) == 0: fltr = None
        else:
            fltr = path
            path = None
        if os.path.abspath(path) == self.cwd: path = None
        if fltr:
            self.browser.filterText = fltr
            self._filter.setText(fltr)
        if path:
            self.browser.open(path)
            self.putCwd()

    @property
    def filterPath(self): return self.browser.abspath(self.filter)

    def _event(self, ev):

        # Change filter criteria...
        if ev.target is self._filter:
            if ev.type in (GuiEvent.ENTER, GuiEvent.BLUR):
                self.gui.focus = self
                self.setFilter(ev)

        # ENTER key...
        elif ev.type == GuiEvent.KEYDOWN:
            if isEnter(ev.original) and self.browser.getSelected():
                ev.type = GuiEvent.SUBMIT

        # Open/Save/Cancel button click...
        elif ev.type == GuiEvent.MOUSEDOWN:
            if ev.target is self.cancel:
                ev.type = GuiEvent.CANCEL
            elif ev.target is self.done:
                if self.browser.getSelected():
                    fn = self.browser.selectedPath
                    if os.path.isdir(fn):
                        if self.mode == FOLDER:
                            ev.type = GuiEvent.SUBMIT
                        else:
                            self.browser.open(fn)
                            ev.type = GuiEvent.CHANGE
                            self.putCwd()
                    elif os.path.exists(fn):
                        ev.type = GuiEvent.SUBMIT
                    else: self.filter = self.initFilter
                elif self.mode == SAVE:
                    fn = self.filterPath
                    if not containsAny(fn): ev.type = GuiEvent.SUBMIT

        # Double-click an item...
        elif ev.type == GuiEvent.DBL_CLICK:
            if isinstance(ev.target, FileItem):
                if os.path.exists(self.browser.abspath(ev.target.name)):
                    ev.type = GuiEvent.SUBMIT
                else: self.filter = self.initFilter
            elif ev.target == self.browser: # FileItem is removed when target is a folder!!
                ev.type = GuiEvent.CHANGE
                self.putCwd()

        # Single-click an item...
        elif ev.type == GuiEvent.SELECT and isinstance(ev.target, FileItem):
            fltr = ev.target.name if os.path.isfile(self.browser.selectedPath) else self.filter
            self._filter.setText(fltr)

        # Confirm file overwrite...
        if self.mode == SAVE and ev.type == GuiEvent.SUBMIT:
            fn = self.browser.selectedPath
            if not fn: fn = self.filterPath
            if os.path.isfile(fn):
                msg = "[{}]\n\nThe current folder already contains a file with this name.\nDo you want to overwrite the file?".format(fn.replace("\\","/").split("/")[-1])
                mb = MsgBox(msg, [" Yes ","No"], title="Overwrite File?")
                mb.bind(type(self).confirm)
                mb.event = ev
                mb.fileDlg = self
                self.gui.place(mb)
                return
        
        # Finish up...
        if self.allowClose and ev.type in (GuiEvent.SUBMIT, GuiEvent.CANCEL): self.close()
        return self.submit(ev) if ev.type == GuiEvent.SUBMIT else self._onEvent(ev)

    @staticmethod
    def confirm(msgBox, ev):
        """Confirm overwrite of existing file"""
        if ev.type == GuiEvent.SUBMIT:
            dlg = msgBox.fileDlg
            if ev.target.index == 0:
                if dlg.allowClose: dlg.close()
                return dlg.submit(msgBox.event)

    def submit(self, ev):
        """End dialog"""
        ev.value = self.browser.selectedPath
        if not ev.value:
            ev.value = self.filterPath
        return self._onEvent(ev)

    def setFilter(self, ev):
        fn = self._filter.txt
        if fn == "": fn = self.initFilter
        self.filter = fn
        if ev.type != GuiEvent.ENTER:
            ev.type = GuiEvent.CHANGE
        path = self.browser.abspath(fn)
        if ev.type == GuiEvent.ENTER and os.path.isfile(path):
            ev.type = GuiEvent.SUBMIT


class Menu(ButtonGrid):
    focusable = True
    parent = None
    posn = 6, 6
    fixedPosn = True

    def __init__(self, items, name=None, posn=None):
        assert len(items) > 0, "Menu must contain at least one item"

        super().__init__((1, len(items)), False, name, posn if posn else Menu.posn)
        self.space = -MenuItem.border
        for item in items: self.place(item)
        self.buttonSize = self.widgets[0].getSize()
        self.startAt(0)

    @property
    def level(self):
        if self.parent:
            c = self.parent.container
            if c: return 1 + c.level
        return 0

    @property
    def main(self):
        if self.parent:
            c = self.parent.container
            if c: return c.main
        return self

    def _event(self, ev):
        gui = self.gui
#        c = ev.target.container
#        if isinstance(ev.target, MenuItem) and c: gui.focus = c
        if ev.type == GuiEvent.KEYDOWN and ev.original.key == pygame.K_ESCAPE:
            ev.type = GuiEvent.ESCAPE
            if self.parent != None:
                gui.close(self)
                gui.place(self.parent.dialog)
        elif ev.type == GuiEvent.MOUSEDOWN:
            if isinstance(ev.target, MenuItem):
                if isinstance(ev.target.link, Menu):
                    gui.close(self)
                    gui.place(ev.target.link)
                elif ev.target._back:
                    gui.close(self)
                    gui.place(ev.target.container.parent.container)
            ev.type = GuiEvent.SELECT
        elif ev.type == GuiEvent.BLUR:
            gui.close(self)
            f = gui.focus
            gui.place(ev.target.main)
            gui.focus = f
        return self._onEvent(ev)

    def linkTo(self, item, find=None):
        if find: item = item.find(find)
        item.link = self
        return self

    def allItems(self):
        for wdg in self.widgets:
            yield wdg
            if wdg.link:
                for w in wdg.link.allItems(): yield w

    def allMenus(self):
        yield self
        for wdg in self.widgets:
            if wdg.link:
                for w in wdg.link.allMenus(): yield w

    @staticmethod
    def make(data, handler=None, posn=None, main=True):
        name, data = data
        if main:
            items = []
            h = fontHeight(MenuItem)
            MenuItem.back = Image(wigsPath("icons/menu.png")).scale((h, h))
        else:
            items = [MenuItem(name, MenuItem.back, iconSize=(1,0)).backLink()]
        for i in data:
            isStr = type(i) == str
            items.append(MenuItem(i if isStr else i[0], iconSize=(0,0)))
            if not isStr:
                items[-1].link = Menu.make(i, handler, posn, False)
        menu = Menu(items, name, posn)
        if handler: menu.bind(handler)
        if main: pass
        return menu


class GridItem(Button):
    textSize = 4
    iconSize = 1, 1
    border = 0
    pad = 2
    bgColor = None

    @classmethod
    def metrics(cls):
        h = fontHeight(cls)
        l, r = cls.iconSize
        e = 2 * (cls.pad + cls.border)
        return (h * l, h), (h * r, h), (h * (l + r + cls.textSize), h), (h * (l + r + cls.textSize) + e, h + e)

    def __init__(self, text=None, icon=None, iconRight=None, textSize=None, iconSize=None, name=None, **kwargs):
        super().__init__(text, name if name else text, **kwargs)
        metric = self.metrics()
        w, h = metric[2]
        imgs = []
        if textSize != None: self.textSize = textSize
        if iconSize != None: self.iconSize = iconSize
        left, right = self.iconSize
        for i in self.data:
            img = Image((w, h))
            i.blitTo(img, (h * left + self.pad, 0))
            if icon: self.fitIcon(icon, metric[0]).blitTo(img)
            if iconRight: self.fitIcon(iconRight, metric[1]).blitTo(img, (w - h * right, 0))
            imgs.append(img)
        self.data = imgs
        self.getSize()

    def fitIcon(self, icon, sz):
        icon = Image(icon)
        if sz != icon.size:
            icon = icon.fit(sz)
        return icon


class FileItem(GridItem):
    textSize = 10
    iconSize = 2, 0
    colors = {
        Widget.DEFAULT: (255,255,255),
        Widget.HOVER: Widget.colors[Widget.HOVER],
        Widget.SELECT: Widget.colors[Widget.SELECT]
    }

class MenuItem(GridItem):
    borderColor = (255,255,255)
    border = Button.border
    pad = Button.pad

    textSize = 4
    iconSize = 1, 0
    _link = None
    _back = False

    @property
    def link(self): return self._link

    @link.setter
    def link(self, menu):
        self._link = menu
        menu.parent = self

    @property
    def index(self):
        if self.container:
            return self.container.widgets.index(self)
        return -1

    @property
    def level(self):
        if self.index < 0: return 0
        if self.container.parent: return 1 + self.container.parent.level
        return 1

    @property
    def main(self):
        return self.container.main if self.container else None

    def backLink(self):
        self._back = True
        return self
