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

"EXPERIMENTAL!!! Create a Canvas from a description stored in a dictionary / JSON file"

import json
from sc8pr import Sketch, Canvas
from sc8pr.shape import Circle, Ellipse, Line, Arrow, Polygon
from sc8pr.plot import plot, gridlines
from sc8pr.text import Font
from sc8pr.util import ondrag
import sc8pr.plot.mpl as mpl


def canvas(data):
    "Create a Canvas instance from data in a dictionary or JSON file"
    if type(data) is str:
        with open(data) as f: data = json.load(f)
    bg = data.get("bg")
    dr = data.get("drag")
    cs = data.get("coords")

    cv = Canvas(data["size"])
    if bg: cv.config(bg=bg)
    if cs:
        cv.attachCS(cs, data.get("margin", 1))
        grid = data.get("grid")
        if grid:
            attr = dict(stroke="lightgrey", weight=1)
            for g in grid:
                a = attr.copy()
                if len(g) > 2: a.update(g[2])
                gridlines(cv, *g[:2], **a)
            if data.get("flatten_grid", True): cv.flatten()

    for item, key, args, cfg in data.get("items", []):
        if item == "circ":
            item = Circle(args) if type(args) in (int, float) else Ellipse(args) 
        elif item == "line": item = Line(*args)
        elif item == "poly": item = Polygon(args)
        elif item == "arrow": item = Arrow(**args)
        elif item == "mpl": item = mpl.text(args[0], **args[1])
        else: key = None
        if key: cv[key] = item.config(**cfg)
        elif item == "plot":
            try:
                cfg = cfg.copy()
                cfg["font"] = Font.find(*cfg.get("font", "").split(","))
            except: pass
            plot(cv, *args, **cfg)
    if dr:
        for gr in cv: gr.bind(ondrag)
    return cv

def save_png(json_fn, png_fn):
    "Convert JSON file data to PNG image"
    with open(png_fn, "wb") as f:
        data = canvas(json_fn).snapshot().png
        f.write(data.read())
