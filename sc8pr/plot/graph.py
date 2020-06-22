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

import json
from math import sin, cos
from sc8pr import TOP, RIGHT, Image
from sc8pr.util import mix, rangef
from sc8pr.text import Font, Text
from sc8pr.shape import Circle
from sc8pr.plot import PCanvas, PBar
from sc8pr.plot.shape import PLocus

def lin(x, k=1, b=0): return k*x + b
def quad(x, a=1, b=0, c=0): return (a * x + b) * x + c
def power(x, a=1, n=1): return a * x ** n
def exp(x, a=1, b=1): return a * b ** x
def sine(x, A=1, k=1, phi=0, y0=0): return A * sin(k * x - phi) + y0
def cosine(x, A=1, k=1, phi=0, y0=0): return A * cos(k * x - phi) + y0

functions = dict(lin=lin, quad=quad, pow=power, exp=exp, sin=sine, cos=cosine)

def cvGraph(data, size=(512, 384)):

    # Load data from JSON file
    if type(data) is str:
        with open(data) as f: data = json.load(f)

    # Create PCanvas with gridlines and axes
    grid = data["grid"]
    step = data.get("gridStep", None)
    margin = data.get("margin", 0)
    cv = PCanvas(size).config(**data.get("config", {}))
    lrbt = cv.viewport(grid, margin) if margin else grid
    cv.setCoords(lrbt)
    if step:
        cv.gridlines(grid, step)
        for gr in cv: gr.role = "grid"
    cv.axis(grid[:2], grid[2:])
    cv.axis = cv[-2]
    for gr in cv[-2:]: gr.role = "axis"

    # Determine fonts
    font = {"fontSize": 18}
    font.update(data.get("font", {}))
    _font(font)
    labelFont = font.copy()
    labelFont.update(data.get("labelFont", {}))

    # Label the x- and y-axis ticks
    label = data.get("xlabel", None)
    if label: cv += _labels(cv, label, mix(rangef(*label["range"]), 0), font, TOP)
    label = data.get("ylabel", None)
    if label: cv += _labels(cv, label, mix(0, rangef(*label["range"])), font, RIGHT)

    # Graph the data
    folders = data.get("folders", {})
    cv.seriesList = []
    for series in data.get("locus", []): _locus(cv, series)
    for series in data.get("series", []):
        if "data" in series:
            sdata = _series(cv, series, font, folders)
        else:
            _markerLabel(cv, series["label"], sdata, labelFont)

    # Add graph and axis titles
    font.update(data.get("titleFont", {}))
    _font(font)
    for title in data.get("titles", []): _title(cv, title, font, folders)

    # Layer all bar graphs underneath the x-axis
    for gr in list(cv.instOf(PBar)): gr.config(layer=cv.axis.layer)
    return cv

def _font(f):
    "Find a requested font"
    found = Font.find(*f["font"].split(","))
    f["font"] = found if found else Font.sans()

def _labels(cv, label, data, font, anchor):
    "Add labels along one axis"
    series = cv.series(data, label["format"], label.get("shift", (0, 0)), **font)
    anchor = label.get("anchor", anchor)
    for gr in series:
        gr.config(role="ticklabel", anchor=anchor)
    return series

def _locus(cv, series):
    "Add a locus (line or curve)"
    data = series["data"]
    param = series.get("param", None)
    if type(data) is str: data = functions[data]
    cv += PLocus(data, param, **series.get("vars", {})).config(role="locus", **series.get("config", {}))

def _series(cv, series, font, folders):
    "Add markers, data labels, or bars"
    config = {}
    marker = series.get("marker", None)
    if marker is None:
        imgs = series["image"]
        if type(imgs) is str: imgs = [imgs]
        cfg = series.get("image_config", {})
        marker = [Image(img.format(**folders)).config(**cfg) for img in imgs]
        if len(marker) == 1: marker = marker[0]
    elif type(marker) is str:
        config = font.copy()
    elif type(marker) is list:
        r = marker[0]
        marker = Circle(10 * r).config(**marker[1]).snapshot().config(height=2*r)
    config.update(series.get("config", {}))
    data = series.get("data")
    sList = cv.series(data, marker, series.get("shift", (0, 0)), **config)
    cv.seriesList.append(sList)
    cv += sList
    for gr in sList: gr.role = "marker"
    return data

def _markerLabel(cv, label, data, font):
    config = font.copy()
    config.update(label.get("config", {}))
    frmt = label["format"]
    shift = label.get("shift", (0, 0))
    sList = cv.series(data, frmt, shift, **config)
    cv.seriesList.append(sList)
    cv += sList
    for gr in sList:
        gr.config(role="label", template=frmt, shift=shift)

def _moveLabel(label, csPos):
    x, y = csPos
    sx, sy = label.shift
    label.config(csPos=(x+sx, y+sy), data=label.template.format(x=x, y=y))

def moveMarkerLabels(markers, labels):
    for m, l in zip(markers, labels): _moveLabel(l, m._xy)

def _title(cv, title, font, folders):
    "Add graph or axis titles"
    if "text" in title:
        gr = Text(title["text"]).config(**font)
    else: # TODO: Pass image rather than text
        gr = Image(title["image"].format(**folders))
    if gr:
        gr.setCanvas(cv).config(role="title", **title.get("config", {}))
    return gr
