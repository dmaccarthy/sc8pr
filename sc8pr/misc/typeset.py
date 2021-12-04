# Copyright 2015-2021 D.G. MacCarthy <http://dmaccarthy.github.io>
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

from sc8pr import LEFT, RIGHT, CENTER, TOPLEFT, TOP, TOPRIGHT, Canvas
from sc8pr.text import Text

def breakLine(text, font, width, chars=" -"):
    "Break a single paragraph into lines to fit into desired width"
    lines = ""
    while len(text):
        ltext = None
        n = len(text)
        spaces = [i for i in range(n) if text[i] in chars] + [n]
        for i in spaces:
            if font.size(text[:i+1])[0] < width:
                ltext = text[:i+1]
            else: break
        if ltext is None:
            try: ltext = text[:spaces[0]+1]
            except: ltext = text
        lines += ("\n" if lines else "") + ltext.strip()
        text = text[len(ltext):].strip()
    return lines

def breakLines(text, font, width, chars=" -"):
    "Break a text into parapgraphs and lines"
    if type(text) is str: text = text.split("\n")
    return [breakLine(t if t else " ", font, width, chars) for t in text]

def typeset(text, width, padding=0, spaceBetween=None, strictWidth=False, chars=" -", **kwargs):
    "Create a canvas containing one or more Text instances"
    attr = {} if "align" in kwargs else {"align": LEFT}
    attr.update(kwargs)
    a = attr["align"]
    if "anchor" not in attr:
        attr["anchor"] = TOPRIGHT if a == RIGHT else (TOPLEFT if a == LEFT else TOP)
    font = Text().config(**attr).renderer
    if spaceBetween is None:
       spaceBetween = 3 * attr.get("spacing", Text.spacing)
    para = breakLines(text, font, width, chars)
    text = [Text(t).config(**attr) for t in para]
    if strictWidth: w = width
    else:
        w = 1
        for t in text:
            if t.width > w: w = t.width
    x = y = padding
    if a != LEFT:
        x += w - 1 if a == RIGHT else (w-1)//2
    for t in text:
        t.config(pos=(x,y))
        y += t.height + spaceBetween
    cv = Canvas((w + 2 * padding, y + padding - spaceBetween))
    cv += text
    return cv
