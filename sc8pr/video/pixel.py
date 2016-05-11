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


from sc8pr.video.effects import Effect
from sc8pr.util import randColor
from pygame.pixelarray import PixelArray
from random import random


class PixelEffect(Effect):

    def transform(self, img, n):
        "Apply pixel-by-pixel effect"
        img = img.clone()
        pxa = PixelArray(img.surface)
        self.mask = img.surface.get_masks()[3]
        c = 0
        for pxCol in pxa:
            for r in range(len(pxCol)):
                px = self.pixel(n, c, r, pxCol[r], img)
                if px: pxCol[r] = px
            c += 1
        return img


class Dissolve(PixelEffect):
    "Dissolve from transparency, solid color, or noise"

    def __init__(self, length, color=False, transparent=False, frame=None):
        super().__init__(length, frame)
        self.color = (0,0,0,0) if color is False else color
        self.transparent = transparent

    def pixel(self, n, x, y, color, img):
        "Calculate pixel color"
        if (self.transparent or color & self.mask) and random() > n:
            return randColor() if self.color is True else self.color


def noise(img, color=True, n=0):
    "Add noise to an image"
    return Dissolve(1, color).transform(img, n)
