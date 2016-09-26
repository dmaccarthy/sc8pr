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


from sc8pr.sketch import Sketch, Sprite
from sc8pr.image import Image
from sc8pr.plot import Plot
from sc8pr.util import rgba, ARROW
from sc8pr.widgets import Widget, MsgBox
from sc8pr.io import USERINPUT
from pygame import MOUSEBUTTONDOWN, MOUSEMOTION

WHITE, RED = rgba("white", "red")
CURSOR_X = ((16,16),(9,9),(0,0,192,3,96,6,48,12,24,24,12,48,6,96,3,192,1,128,3,192,6,96,12,48,24,24,48,12,96,6,192,3),(0,0,192,3,96,6,48,12,24,24,12,48,6,96,3,192,1,128,3,192,6,96,12,48,24,24,48,12,96,6,192,3))
CURSOR_O = ((16,16),(9,8),(3,192,14,112,24,24,48,12,96,6,96,6,192,3,192,3,192,3,96,6,96,6,48,12,24,24,14,112,3,192,0,0),(3,192,14,112,24,24,48,12,96,6,96,6,192,3,192,3,192,3,96,6,96,6,48,12,24,24,14,112,3,192,0,0))

def board(sk):
    "Draw the Tic-Tac-Toe board"
    h = sk.height
    marg = h * 5 // 100
    img = Plot(Image((h,h), WHITE), (0,3), (0,3), marg)
    lines = [(0,1), (3,1)], [(0,2), (3,2)], [(1,0), (1,3)], [(2,0), (2,3)]
    for line in lines: img.plot(line, strokeWeight=3)
    return img

def xo(sk):
    "Create the X and O sprites"
    img = Image("sprites.png").tiles(3)
    bg = sk.bgImage
    h = bg.unit["x"]
    for x in range(3):
        for y in range(3):
            posn = bg.coords((x + 0.5, y + 0.5))
            Sprite(sk, img, posn=posn, height=h)

def owner(sk, *args):
    "Check which player owns the specified square(s)"
    p = sk.sprites[args[0]].currentCostume
    for i in args[1:]:
        if sk.sprites[i].currentCostume != p:
            return None
    return p

def click(sk, ev):
    "Mouse click event handler"
    s = sk.sprites.at(sk.mouseXY)
    if s and s.currentCostume == 0:
        s.currentCostume = sk.player
        sk.player = 3 - sk.player
        w = winner(sk)
        n = len([s for s in sk.sprites if s.currentCostume == 0])
#        n = len(sk.sprites.search(currentCostume=0))
        if w or n == 0:
            title = "Player {} Wins!".format(w) if w else "Draw!"
            sk.prompt("Play again?", validator=bool, title=title, borderColor=RED, minSize=(192,72))
        setCursor(sk)

def playAgain(sk, ev):
    "Restart or quit the game"
    if ev.value:
        sk.player = 1
        sk.sprites.config(currentCostume = 0)
    else: sk.quit = True

def setCursor(sk, ev=None):
    "Change cursor based on turn and mouse location"
    s = sk.sprites.at(sk.mouseXY)
    n = owner(sk, s.index) == 0 if s else False
    sk.cursor = (CURSOR_X, CURSOR_O)[sk.player - 1] if n else ARROW

def winner(sk):
    "Determine the winner"
    cols = (0,1,2), (3,4,5), (6,7,8)
    rows = (0,3,6), (1,4,7), (2,5,8)
    diag = (0,4,8), (2,4,6)
    for combo in rows + cols + diag:
        w = owner(sk, *combo)
        if w: return w

def setup(sk):
    "Initialize the sketch"
    sk.setBackground(board(sk))
    xo(sk)
    sk.player = 1
    sk.animate(eventMap={MOUSEBUTTONDOWN:click, USERINPUT:playAgain, MOUSEMOTION:setCursor})
    Widget.font = sk.loadFont("sans", 16)
    MsgBox.font = sk.loadFont("sans", 20, True)

Sketch(setup).play((640,640), "Tic-Tac-Toe")
