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

"Draw and save 2D vector diagrams"

from sc8pr import version
if 100 * version[0] + version[1] < 202:
    raise NotImplementedError("This program requires sc8pr 2.2; installed version is {}.{}.".format(*version[:2]))

import os, json
from sc8pr import Sketch, TOP, CENTER, TOPLEFT, BOTTOMRIGHT, TOPRIGHT
from sc8pr.util import ondrag, nothing, logError, modKeys, dragDrop
from sc8pr.text import Font, Text
from sc8pr.plot import PCanvas
from sc8pr.plot.shape import PVector
from sc8pr.gui.textinput import TextInputCanvas
from sc8pr.gui.dialog import Dialog
from sc8pr.gui.button import Button
from sc8pr.gui.radio import Options


class _VectorUI(Dialog):
    "Create the UI dialog"
    drawTitle = False
    buttonWidth = 96
    padding = 8
    
    def __init__(self, size, buttons=(("Okay", True), ("Cancel", False)), text={}, **kwargs):
        py = p = self.padding
        super().__init__((size, 128))
        self.config(vectors=None, **kwargs)
        if self.drawTitle: self.title("Vector Diagram")

        # Text options
        txtConfig = {"font":Font.sans(), "fontSize":15}
        txtConfig.update(text)

        # Text inputs
        w = self.width - 2 * p
        try: y = py + self[0].height
        except: y = py
        ti = TextInputCanvas(w, "", "Vector Expression", **txtConfig)
        self["Vectors"] = ti.config(anchor=TOPLEFT, pos=(p, y), weight=1).bind(onaction=self.parse)
        y += py + ti.height
        self["Grid"] = TextInputCanvas(w // 2 - p, "", "Grid Settings", **txtConfig).config(anchor=TOPLEFT, pos=(p, y), weight=1)
        self["Step"] = TextInputCanvas(w // 4 - p // 2, "", "Step", **txtConfig).config(anchor=TOPLEFT, pos=(p + w // 2, y), weight=1)
        self["Size"] = TextInputCanvas(w // 4 - p // 2, "", "Width", **txtConfig).config(anchor=TOPLEFT, pos=(3 * (2 * p + w) // 4, y), weight=1)
        for gr in self[-3:]: gr.bind(onaction=nothing)

        # Options
        y += py + self[-1].height
        text = "Resultant", "Components", "Draggable"
        opt = Options(text, txtConfig=txtConfig).config(pos=(p, y), anchor=TOPLEFT)
        self["Options"] = opt
        x = (self.width - opt.width - p - w) / 2
        x = self.width - x - w / 2
        y += p
        y0 = y + opt.height
        opt[0].selected = True
        for gr in opt[:3]: gr.bind(onaction=nothing)

        # Buttons
        w = self.buttonWidth
        for btn in buttons:
            name = btn if type(btn) is str else btn[0]
            gr = Button((w, 32), 2).textIcon(*btn).setCanvas(self, name).config(anchor=TOPRIGHT, pos=(self.width - p, y)) #, pos=(x - 64, y))
            y += 32 + py
            gr[-1].config(color="blue", align=CENTER, **txtConfig)

        # Resize
        self._size = size, max(y, y0)

    @staticmethod
    def parse(ti, ev):
        cv = ti.canvas
        try:
            cv.vectors = PVector.parse(ti.data)
            data = "{:.2g}, {:.2g}, {:.2g}, {:.2g}".format(*_VectorUI.region(cv.vectors))
        except:
            cv.vectors = None
            data = "Parse error!"
        cv["Grid"].config(data=data)

    @staticmethod
    def region(vecs):
        x0, y0 = vecs[0].tail
        x1 = x0
        y1 = y0
        for v in vecs:
            x, y = v.tip
            if x < x0: x0 = x
            elif x > x1: x1 = x
            if y < y0: y0 = y
            elif y > y1: y1 = y
        return x0, x1, y0, y1


class VectorUI(_VectorUI):
    "Implement onaction handler: render the vector diagram"

    lastDiagram = None
    cfg = {"axis":{}, "grid":{}, "vector":{},
        "resultant":{"stroke":"blue"}, "component":{"stroke":"green"}}

    @staticmethod
    def style(v, mode=0):
        v.config(**VectorUI.cfg["vector"])
        if mode == 1: v.config(**VectorUI.cfg["resultant"])
        elif mode == 2: v.config(**VectorUI.cfg["component"])
        return v

    @staticmethod
    def diagram(vecs, width, lrbt=None, step=1, bg="white", flatten=True,
            resultant=True, components=False, draggable=False, **kwargs):
        "Draw vectors on a PCanvas"
        if type(vecs) is str: vecs = PVector.parse(vecs)
        for v in vecs: VectorUI.style(v)
        if isinstance(width, PCanvas): cv = width
        else:
            x0, x1, y0, y1 = lrbt
            dx = (x1 - x0) / 100
            dy = (y1 - y0) / 100
            cv = PCanvas(width, [x0-dx, x1+dx, y0-dy, y1+dy], bg=bg)
            cv.gridlines(lrbt, step, VectorUI.cfg["axis"], **VectorUI.cfg["grid"])
        cv.config(**kwargs)
        if flatten: cv.flatten()
        if components:
            for v in vecs:
                vx, vy = v.components()
                x, y = vx.mag, vy.mag
                m = max(x, y)
                if m and min(x, y) > m / 500:
                    for v in (vx, vy): cv += VectorUI.style(v, 2)
        cv += vecs
        if resultant:
            cv.resultant = v = PVector.sum(vecs)
            if len(vecs) > 1:
                VectorUI.style(v, 1).config(tail=vecs[0].tail).setCanvas(cv)
        else: cv.resultant = None
        if draggable:
            for v in cv.config(allowDrop=True).instOf(PVector):
                v.bind(ondrag=dragDrop)
        return cv

    def onaction(self, ev):
        try: size = int(self["Size"].data)
        except: size = 384
        try: step = float(self["Step"].data)
        except: step = None
        try:
            lrbt = [float(x.strip()) for x in self["Grid"].data.split(",")]
            if step is None: step = (lrbt[1] - lrbt[0]) / 10
            opt = self["Options"]
            opt = dict(
                resultant = opt[0].selected,
                components = opt[1].selected,
                draggable = opt[2].selected
            )
            self.lastDiagram = self.diagram([PVector(v) for v in self.vectors], size, lrbt, step, bg="white", **opt)
        except:
            self.lastDiagram = None
            logError()


class VectorApp(VectorUI):
    "Modify dialog's onaction method to run as standalone app"

    def onaction(self, ev):
        super().onaction(ev)
        sk = self.sketch
        pos = sk.width - 8, sk.height - 10
        cv = self.lastDiagram
        if cv:
            sk += cv.config(pos=pos, anchor=BOTTOMRIGHT).bind(ondrag, onclick=self.click)
            if cv.resultant: print(str(cv.resultant)[9:-1])

    @staticmethod
    def click(cv, ev):
        m = modKeys()
        if m & 4:
            font = dict(font=Font.sans(), color="red", fontSize=18)
            i = 0
            fn = "vector{}.png"
            while os.path.exists(fn.format(i)): i += 1
            fn = fn.format(i)
            cv.save(fn).removeItems("Saved")
            cv["Saved"] = Text("Saved as '{}'".format(fn)).config(anchor=TOP, pos=(cv.center[0], 8), **font)
        elif m & 1: cv.remove()
        else: cv.config(layer=-1)


class VectorSketch(Sketch):

    def setup(self):
        cv = VectorApp(384, [("Draw!", True)], weight=2, border="blue").config(pos=(4,4), anchor=TOPLEFT)
        btn = list(cv.instOf(Button))[0]
        btn.config(pos=(cv.width - 8, cv.height - 8), anchor=BOTTOMRIGHT)
        self += cv
        self.config(resizeContent=False, fixedAspect=False)


try:
    with open("vector2d.json") as f: VectorUI.cfg = json.load(f)
except: pass
if __name__ == "__main__":
    VectorSketch((800, 600)).play("Vector Diagrams 2D")
