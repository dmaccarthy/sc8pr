# Copyright 2019-2021 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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

"""
This program demonstrates how a Graphic can be used in place
of a cursor. The program relies on the Graphic.hoverable
property which has been added in the development version of
sc8pr (v2.2) but has not been released as of v2.1. If used
in an earlier sc8pr version, the "cursor" will block mouse events
to other graphic objects.
"""

from sc8pr import Sketch
from sc8pr.util import resolvePath
from sc8pr.sprite import Sprite

class FakeCursor(Sketch):

    @staticmethod
    def updateFakeCursor(gr):
        "Run default ondraw and configure to follow the mouse"
        h = type(gr).ondraw
        if h: h(gr)
        gr.config(pos=gr.sketch.mouse.pos, layer=-1)

    def fakeCursor(sk, gr):
        "Use a graphic to mimic the cursor"
        sk.cursor = False
        sk += gr.bind(ondraw=sk.updateFakeCursor).config(hoverable=False, wrap=0)

    def setup(sk):
        gr = Sprite(resolvePath("img/ship.png", __file__)).config(width=32, spin=1)
        sk.fakeCursor(gr)

def play(): FakeCursor().play("Fake Cursor")

if __name__ == "__main__": play()
