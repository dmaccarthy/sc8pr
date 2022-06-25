# Copyright 2015-2022 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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

"A collection of functions for plotting data on canvases"

from sc8pr import Image, Graphic
from sc8pr.text import Text
from sc8pr.shape import Circle, Line, Polygon

def _data(x, y=None):
    "Get data as sequence of (x, y) tuples"
    if type(x) in (int, float): x = len(y) * [x]
    if type(y) in (int, float): y = len(x) * [y]
    return zip(x, y) if y else x

def _marker(m, x, y, i):
    m = m[i]
    if type(m) is str:
        m = Text(m.format(x=x, y=y))
    return m

def plot(cv, x, y=None, markers=5, offset=None, **kwargs):
    "Draw markers (Graphic instances) at a sequence of points"
    data = _data(x, y)
    if type(markers) is int:
        h = 2 * markers
        markers = Circle(1).config(radius=max(32, markers), **kwargs).snapshot()
        kwargs = {"height": h}
    if type(markers) is str:
        marker = lambda *i: Text(markers.format(x=i[0], y=i[1])).config(**kwargs)
    elif isinstance(markers, Graphic):
        markers = Image(markers)
        marker = lambda *i: Image(markers).config(**kwargs)
    else:
        marker = lambda *i: _marker(markers, *i).config(**kwargs)
    i = 0
    dx, dy = (0, 0) if offset is None else offset
    for x, y in data:
        cv += marker(x, y, i).config(xy=(x+dx, y+dy))
        i += 1
    return i

def bars(cv, x, y=None, width=1, **kwargs):
    "Draw bar graph data"
    i = 0
    for x, y in _data(x, y):
        x0 = x - width / 2
        x1 = x + width / 2
        pts = (x0, 0), (x1, 0), (x1, y), (x0, y)
        cv += Polygon(pts, anchor=(x,y)).config(**kwargs)
        i += 1
    return i

def _gridlines(cv, x, y, dim, **config):
    "Draw gridlines in EITHER x or y direction"
    x0, x1, x2 = x
    y0, y1 = y[:2]
    i = 0
    if x0 > x1: x0, x1 = x1, x0
    while x0 <= x1:
        pts = [(y0, x0), (y1, x0)] if dim else [(x0, y0), (x0, y1)]
        cv += Line(*pts).config(**config)
        x0 += x2
        i += 1
    return i

def gridlines(cv, x=(0,1,2), y=(0,1,2), **config):
    "Draw gridlines (or an axis) on a canvas"
    i = 0
    if len(x) > 2: i += _gridlines(cv, x, y, 0, **config)
    if len(y) > 2: i += _gridlines(cv, y, x, 1, **config)
    return i
