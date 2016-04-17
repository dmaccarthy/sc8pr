# Copyright 2015-2016 D.G. MacCarthy <devwigs@gmail.com>
#
# This file is part of WIGS.
#
# WIGS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# WIGS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with WIGS.  If not, see <http://www.gnu.org/licenses/>.


from wigs.video.video import ImageSeq
from wigs.image import Image
from wigs.util import randColor
from pygame import PixelArray
from random import random

class NoiseSeq(ImageSeq):
    "A class to generate a sequence of random noise images"

    turnover = 0.08

    def __init__(self, size, frames=None, **kwargs):
        self.img = Image(size, alpha=False)
        self.image(True)
        self._frames = frames
        self.__dict__.update(kwargs)

    def image(self, n):
        pxa = PixelArray(self.img.surface)
        for pxCol in pxa:
            for r in range(len(pxCol)):
                if n is True or (n > 0 and random() < self.turnover):
                    pxCol[r] = randColor()    
        return self.img

    def __len__(self): return self._frames

    @property
    def size(self): return self.img.size


def noiseImage(size):
    "Create a single image of random noise"
    return NoiseSeq(size).image(0)
