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


from random import randint
from sc8pr import Sketch, Image, TOPLEFT, TOPRIGHT, BOTTOM
from sc8pr.text import Text, Font, BOLD
from sc8pr.gui.button import Button
from sc8pr.util import resolvePath

def setup(sk):
    # Load image originals
    fldr = resolvePath("img", __file__)
    sk.imgs = [Image("{}/{}.png".format(fldr, f))
        for f in ("target", "paper", "scissors")]

    # Create button controls and add images to buttons
    w, h = sk.size
    x = w / 4 - 44
    for img in sk.imgs:
        btn = Button((40, 40), 2).config(anchor=BOTTOM, pos=(x, h-4))
        btn += Image(img).config(pos=btn.center, height=32)
        sk += btn.bind(onclick) # Bind event handlers
        x += 44

    # Initialize scores to zero
    font = {"font":Font.mono(), "fontSize":40, "fontStyle":BOLD}
    sk["Score1"] = Text(0).config(color="red", anchor=TOPLEFT, pos=(4, 4), **font)
    sk["Score2"] = Text(0).config(color="blue", anchor=TOPRIGHT, pos=(w-4, 4), **font)

    # Create status text
    sk["Status"] = Text("Make a choice!").config(pos=(0.75*w, h-24),
        font=Font.sans(), fontSize=32, color="red")

def onclick(btn, ev):
    "Event handler for button clicks"

    # Remove images from previous round
    sk = btn.sketch
    try: sk -= sk["Player1"], sk["Player2"]
    except: pass # Nothing to remove in first round!

    # Add images for current round
    p1, p2 = btn.layer, randint(0,2)
    w, h = sk.size
    x, y, h = w / 4, h / 2, 0.6 * h
    sk["Player1"] = Image(sk.imgs[p1]).config(height=h, pos=(x, y))
    sk["Player2"] = Image(sk.imgs[p2]).config(height=h, pos=(3 * x, y))

    # Determine the winner and update scores/status
    if p1 == p2: win = "It's a draw!"
    elif p1 - p2 in (1, -2):
        win = "You win!"
        sk["Score1"] += 1
    else:
        win = "You lose!"
        sk["Score2"] += 1
    sk["Status"].config(data=win, layer=-1)

def onkeydown(sk, ev):
    "Redirect keydown event to button onclick handler"
    try: onclick(sk["rps".index(ev.unicode.lower())], ev)
    except: pass

# Play the game!
Sketch().bind(setup, onkeydown).play("Rock, Paper, Scissors")
