# Copyright 2015-2021 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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

"Convert matplotlib figures to sc8pr.Image or PNG data"

import pygame, io, sys
from sc8pr import Image
from sc8pr.text import Font

plt = sys.modules["matplotlib.pyplot"]

def sc8prFonts():
    "Use sc8pr default fonts with matplotlib"
    p = plt.rcParams
    p["font.serif"][:0] = Font._serif
    p["font.sans-serif"][:0] = Font._sans
    p["font.monospace"][:0] = Font._mono

def figure(fig, dpi=150, image=True):
    "Covert a matplotlib figure to a sc8pr.Image or PNG data"
    png = io.BytesIO()
    fig.savefig(png, dpi=dpi, transparent=True, format="png", bbox_inches="tight", pad_inches=0.0)
    png.seek(0)
    return Image(pygame.image.load(png, "a.png")) if image else png.read()

def text(text, color="black", fontsize=12, dpi=300, image=True):
    "Use matplotlib to render text/math as a sc8pr.Image or PNG data"
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, text, fontsize=fontsize, color=color)
    return figure(fig, dpi, image)
