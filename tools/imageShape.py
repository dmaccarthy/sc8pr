# Copyright 2015-2016 D.G. MacCarthy <http://dmaccarthy.github.io>
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

from sc8pr.sketch import Sketch, OPEN
from sc8pr.util import rgba
from sc8pr.image import Image
from sc8pr.io import USERINPUT
from pygame.constants import MOUSEBUTTONDOWN

WHITE, RED = rgba("white", "red")

def setup(sk):
    sk.setBackground(None, WHITE)
    sk.fileDialog(OPEN, True, "<Image>")
    sk.animate(eventMap={USERINPUT:start})

def start(sk, ev):
    img = Image(ev.value)
    sk.size = img.size
    bg = Image(img.size, WHITE)
    img.blitTo(bg)
    sk.setBackground(bg)
    sk.dot = Image.ellipse(2, RED)
    sk.poly = []
    sk.animate(draw, {MOUSEBUTTONDOWN:mouse})

def mouse(sk, ev): sk.poly.append(ev.pos)

def draw(sk):
    sk.simpleDraw()
    if len(sk.poly) > 2:
        Image(sk.surface).plot(sk.poly, strokeWeight=2, stroke=RED, closed=True)

print(Sketch(setup).play((800,600), mode=0).poly)