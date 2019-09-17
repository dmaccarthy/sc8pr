# Copyright 2015-2019 D.G. MacCarthy <http://dmaccarthy.github.io>
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

from sc8pr import Canvas, Image, BOTTOM, TOP, TOPLEFT
from sc8pr.text import Text
from sc8pr.shape import Line


class BarChart(Canvas):
    format = "{:.1f}"
    scale = 100
    showScale = False
    showValues = True
    space = 6
    _margin = 0, 0, 0, 0
    txtConfig = {}

    @property
    def margin(self): return self._margin

    @margin.setter
    def margin(self, m):
        if type(m) is int: self._margin = 4 * (m,)
        elif len(m) == 4: self._margin = m
        else: self.margin = m[0], m[0], m[1], m[1]

    def resize(self, size):
        size = max(1, round(size[0])), max(1, round(size[1]))
        fx, fy = size[0] / self._size[0], size[1] / self._size[1]
        self.space *= fy
        m = self._margin
        self._margin = fx * m[0], fx * m[1], fy * m[2], fy * m[3]  
        super().resize(size)

    def data(self, data, scale=False):
        self.purge()

        # Add labels to canvas and determine maximum label height
        labelHeight = i = 0
        for item in data:
            label = item["label"]
            if type(label) is str:
                label = Text(label).config(**self.txtConfig)
            self["Label{}".format(i)] = label
            i += 1
            h = label.height
            if h > labelHeight: labelHeight = h

        # Calculate graph metrics
        mx1, mx2, my1, my2 = self._margin
        dx = (self.width - mx1 - mx2) / (2 * i + 1)
        x = mx1 + 1.5 * dx
        y = self.height - my2 - labelHeight - self.space
        if scale is False: scale = self.scale
        elif scale is True: scale = 1.1 * max(item["value"] for item in data)
        self.scale = scale
        scale /= y - my1

        # Add bars; position bars and labels
        i = 0
        for item in data:
            label, val = [item[key] for key in ("label", "value")]
            self[i].config(pos=(x, y + self.space), anchor=TOP)
            h = round(val / scale)
            if h > 0:
                c = item.get("bar", "#ff3030")
                self["Bar{}".format(i)] = Image((dx, h), c).config(pos=(x,y), anchor=BOTTOM)
            if self.showValues:
                txt = self.format.format(val)
                self["Value{}".format(i)] = Text(txt).config(pos=(x, y - h), anchor=BOTTOM, **self.txtConfig)
            i += 1
            x += 2 * dx

        # Axes
        self["xaxis"] = Line((mx1, y), (self.width - mx2, y)).config(weight=2)
        self["yaxis"] = Line((mx1, y), (mx1, my1)).config(weight=2)
        if self.showScale:
            x = mx1 + self.space
            txt = self.format.format(self.scale)
            self["Scale"] = Text(txt).config(pos=(x, my1), anchor=TOPLEFT, **self.txtConfig)
        return self
