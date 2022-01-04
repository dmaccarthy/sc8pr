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


import pygame
from sc8pr import Image

def _allPixels(px, c):
    "Check if all pixels in a column are equal to the specified value"
    return max(px) == c and min(px) == c

def _h_crop(pxa, c):
    "Find blank PixelArray columns"
    n = len(pxa)
    i = 0
    j = n - 1
    while i < n and _allPixels(pxa[i], c): i += 1
    while j > i and _allPixels(pxa[j], c): j -= 1
    return i, j, n

def autocrop(srf, bg=True, replace=None):
    "Crop image to content"
    if type(srf) is str: srf = Image(srf)
    img = isinstance(srf, Image)
    if img: srf = srf.image
    pxa = pygame.PixelArray(srf)
    if bg is True: bg = pxa[0][0]
    elif type(bg) is not int: bg = srf.map_rgb(pygame.Color(bg))
    i, j, n = _h_crop(pxa, bg)
    if i or j < n - 1:
        h = srf.get_size()[1]
        srf = srf.subsurface([i, 0, j - i + 1, h])
        pxa = pygame.PixelArray(srf)
    pxa = pxa.transpose()
    i, j, n = _h_crop(pxa, bg)
    if i or j < n - 1:
        h = srf.get_size()[0]
        srf = srf.subsurface([0, i, h, j - i + 1])
    if replace: pygame.PixelArray(srf).replace(bg, pygame.Color(replace))
    return Image(srf)
