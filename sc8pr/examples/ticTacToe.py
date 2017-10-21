# Copyright 2017 D.G. MacCarthy <http://dmaccarthy.github.io>
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


if __name__ == "__main__": import _pypath
import os
from sc8pr import Sketch, Image, Graphic
from sc8pr.shape import Line
from sc8pr.sprite import Sprite
from sc8pr.gui.tkdialog import TkDialog

TITLE = "Tic-Tac-Toe"

def setup(game):
    "Create Tic-Tac-Toe board with 100 pixel squares and 20 pixel margins"

    # Load costumes for X and O sprites
    img = Image("img/xo.png").tiles(3)

    # Create and position sprites, one per square
    for s in range(9):
        pos = 70 + 100 * (s % 3), 70 + 100 * (s // 3)
        game += Sprite(img).bind(contains=Graphic.contains,
            onclick=clickSquare).config(pos=pos, width=100)

    # Draw the board and start game
    for pts in [((20,120), (320,120)), ((20,220), (320,220)),
        ((120,20), (120,320)), ((220,20), (220,320))]: game += Line(*pts)
    startGame(game)

def startGame(game):
    "Set initial game state"
    game.playerWin = None
    game.playerTurn = 1
    for sp in game.sprites(): sp.costumeNumber = 0

def clickSquare(sprite, ev):
    "Handle CLICK events on any square"
    if sprite.costumeNumber == 0: # Square is vacant?
        game = sprite.sketch

        # Assign square to current player
        n = game.playerTurn
        sprite.costumeNumber = n

        # Check for game over
        if winner(list(game.sprites()), n): game.playerWin = n
        elif 0 not in [sp.costumeNumber for sp in game.sprites()]:
            game.playerWin = 0
        else: game.playerTurn = 3 - n 

def winner(sprites, n):
    "Check if player n occupies 3 squares in a row"
    for sq in [(0,1,2), (3,4,5), (6,7,8), (0,3,6),
            (1,4,7), (2,5,8), (0,4,8), (2,4,6)]:
        if sum(1 for s in sq if sprites[s].costumeNumber == n) == 3:
            return True

def ondraw(game):
    "Check game over status after each frame"
    n = game.playerWin
    if n is not None:
        msg = "Player {} Wins".format(n) if n else "It's a tie"
        if TkDialog(bool, msg + "!\nPlay again?", TITLE).run(): startGame(game)
        else: game.quit = True

def main():
    os.chdir(os.path.dirname(__file__))
    Sketch((340,340)).bind(ondraw).play(TITLE)

if __name__ == "__main__": main()
