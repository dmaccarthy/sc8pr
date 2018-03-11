# Copyright 2015-2018 D.G. MacCarthy <http://dmaccarthy.github.io>
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

"Additional features that use the Pillow (PIL) package"

from PIL import ImageGrab, Image as PImage
from io import BytesIO
from sc8pr import Image
from sc8pr.misc.video import convert
import pygame


def encode(img, frmt="PNG"):
    "Use PIL to encode an image as a BytesIO instance"
    if not isinstance(img, PImage.Image):
        img = convert(img, 3)
    b = BytesIO()
    img.save(b, frmt)
    b.seek(0)
    return b


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

    def image(self, frmt=None):
        "Grab (and convert) an image using PIL.ImageGrab"
        img = ImageGrab.grab(self.bbox)
        if frmt == 2: return Image(convert(img, 2))
        if frmt not in (3, False): img = convert(img, frmt)
        return img
