#!python3

# Copyright 2015-2016 D.G. MacCarthy <http://dmaccarthy.github.io>
#
# This file is part of "sc8pr_gallery".
#
# "sc8pr_gallery" is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "sc8pr_gallery" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "sc8pr_gallery".  If not, see <http://www.gnu.org/licenses/>.


from sc8pr.sketch import Sprite, Sketch
from sc8pr.image import Image
from sc8pr.util import rgba
from sc8pr.geom import add, mag
from random import uniform
from pygame import MOUSEBUTTONUP, KEYDOWN

ELAS = 1.0
WHITE, BLUE, RED, BLACK = rgba("white", "blue", "red", "black")
T_BLUE, T_RED, T_PURPLE = rgba("#0000ff80", "#ff000080", "#80008080") 

def rVel(v=3): return uniform(-v, v), uniform(-v, v)

def setup(sk):
    sk.wall = BLUE
    sk.setBackground(Image(sk.size, WHITE))
    img = Image.ellipse(48, fill=RED)
    red = set()
    for i in range(12):
        p = add((uniform(-100,100), uniform(-100,100)), sk.center)
        Sprite(sk, img, red, height=24, mass=2,
            posn=p, velocity=rVel(1)).circle()
    img = Image.ellipse(48, fill=BLUE)
    blue = set()
    for i in range(48):
        Sprite(sk, img, blue, height=16, mass=1,
            posn=sk.randPixel(), velocity=rVel()).circle()
    sk.sprites.run = False
    sk.sprites.config(elasticity=ELAS)
    sk.animate(draw, {MOUSEBUTTONUP:start, KEYDOWN:keyPress})
    sk.data = [red, blue, False]

def start(sk, ev):
    sk.sprites.run = True

def keyPress(sk, ev):
    if sk.keyCode == 27:
        sk.data[2] = not sk.data[2]
    else:
        sk.sprites.run = not sk.sprites.run

def energy(grp):
    E = 0
    for s in grp:
        E += s.mass * mag(s.velocity, 2)
    return E / 2

def draw(sk):
    sk.physicsDraw()
    r, b, show = sk.data
    if show:
        nr, nb = len(r), len(b)
        r, b = energy(r) / nr, energy(b) / nb
        a = (nr * r + nb * b) / (nr + nb)
        s = 20
        h = sk.hRatio
        w = s / a * 8 * h
        x = 10 * h
        style = dict(stroke=BLACK, strokeWeight=2)
        Image.rect((round(w*r),s*h), fill=T_RED, **style).blitTo(sk.surface, (x,x))
        Image.rect((round(w*b),s*h), fill=T_BLUE, **style).blitTo(sk.surface, (x,h*(10+s)-2))
        Image.rect((round(w*a),s*h), fill=T_PURPLE, **style).blitTo(sk.surface, (x,h*(10+2*s)-4))

Sketch(setup).play((512,384), "Brownian Motion")
