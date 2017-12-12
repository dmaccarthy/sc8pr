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

"""Perform screen captures using PIL.ImageGrab and convert to sc8pr.Image;
Usage...
    Grabber(rect).image(mode, alpha) --> sc8pr.Image
    Grabber(rect).image(None) --> PIL.Image
"""

from PIL import ImageGrab
from io import BytesIO
import pygame
from sc8pr import Image
from sc8pr.util import hasAlpha


class Grabber:
    "A class for performing screen captures using PIL.ImageGrab"
    
    def __init__(self, rect=None):
        if rect and not isinstance(rect, pygame.Rect):
            if len(rect) == 2: rect = (0, 0), rect
            rect = pygame.Rect(rect)
        self.rect = rect

    @property
    def bbox(self):
        "Bounding box for capture"
        r = self.rect
        if r: return [r.left, r.top, r.right, r.bottom]

    @staticmethod
    def encode(img, mode="TGA"):
        "Convert PIL image to TGA, PNG, or another supported format as BytesIO"
        b = BytesIO()
        img.save(b, mode)
        b.seek(0)
        return b

    def image(self, mode=0, alpha=False, img=None):
        "Grab and/or convert an image using PIL.ImageGrab"
        # None = PIL.Image
        # 0 = sc8pr.Image using tobytes
        # 1 = sc8pr.Image using TGA conversion
        # 2 = Uncompressed binary data
        if img is None:
            img = ImageGrab.grab(self.bbox)
            if mode is None: return img
        if mode == 1:
            srf = pygame.image.load(self.encode(img), "foo.tga")
        else:
            srf = img.tobytes()
            if mode == 0:
                srf = pygame.image.fromstring(srf, img.size, img.mode)
            else: return srf, img.mode, img.size
        if alpha and not hasAlpha(srf): srf = srf.convert_alpha()
        return Image(srf)
