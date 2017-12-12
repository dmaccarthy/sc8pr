# Copyright 2015-2017 D.G. MacCarthy <http://dmaccarthy.github.io>
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


from PIL import ImageGrab
from io import BytesIO
import pygame
from sc8pr import Image
from sc8pr.util import hasAlpha

# Usage: Grabber(size, pos).image(mode, alpha) --> sc8pr.Image


class Grabber:
    "A class for performing screen captures using PIL.ImageGrab"
    
    def __init__(self, size=None, pos=(0,0)):
        self.size = size
        self.pos = pos

    @property
    def bbox(self):
        "Bounding box for capture"
        if self.size:
            w, h = self.size
            x, y = self.pos
            b = [x, y, x+w, y+h]
        else: b = None
        return b

    def grabPIL(self): return ImageGrab.grab(self.bbox)

    @staticmethod
    def encode(img, mode="TGA"):
        "Convert PIL image to TGA, PNG, or another supported format as BytesIO"
        b = BytesIO()
        img.save(b, mode)
        b.seek(0)
        return b

    def image(self, mode=0, alpha=False):
        # 0 Image using tobytes
        # 1 Image using TGA conversion
        # 2 Uncompressed binary data
        img = self.grabPIL()
        if mode == 1:
            tga = self.encode(img)
            srf = pygame.image.load(tga, "foo.tga")
        else:
            srf = img.tobytes()
            if mode == 0:
                srf = pygame.image.fromstring(srf, img.size, img.mode)
            else:
                return srf, img.mode, img.size
        if alpha and not hasAlpha(srf): srf = srf.convert_alpha()
        return Image(srf)
