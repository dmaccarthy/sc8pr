# Copyright 2015-2023 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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

import pygame, io, matplotlib as mp, matplotlib.figure as mf
from sc8pr import Image

def fonts(math="stix", sans=None, serif=None, mono=None):
    p = mp.rcParams
    if math: p["mathtext.fontset"] = math
    if sans: p["font.sans-serif"] = sans
    if sans: p["font.serif"] = serif
    if mono: p["font.monospace"] = mono

def figure(fig, image=True, **kwargs):
    "Covert a matplotlib figure to a sc8pr.Image or PNG data"
    png = io.BytesIO()
    attr = dict(dpi=300, transparent=True, bbox_inches="tight", pad_inches=0.025)
    attr.update(kwargs)
    fig.savefig(png, format="png", **attr)
    png.seek(0)
    return Image(pygame.image.load(png, "a.png")) if image else png.read()

def text(text, color="black", fontsize=12, image=True, **kwargs):
    "Use matplotlib to render text/math as a sc8pr.Image or PNG data"
    fig = mf.Figure(figsize=(0.01, 0.01))
    fig.text(0, 0, text, fontsize=float(fontsize), color=color)
    return figure(fig, image, **kwargs)
