# Copyright 2018 D.G. MacCarthy <http://dmaccarthy.github.io>
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

"Render LaTeX using codecogs.com"

from threading import Thread
from io import BytesIO
from time import sleep
from urllib.request import urlopen
from urllib.parse import quote
import pygame

class CodeCogs(Thread):
    "Send request to codecogs.com in a separate thread"
    data = None
    _url = "https://latex.codecogs.com/png.latex?"

    def __init__(self, latex, onload=None):
        self.url = self._url + quote(latex)
        self.onload = onload
        super().__init__()

    def run(self):
        data = BytesIO(urlopen(self.url).read())
        srf = pygame.image.load(data, "x.png")
        self.data = self.onload(srf) if self.onload else srf


def _waiting(imgs):
    "Check whether there are responses pending"
    for img in imgs:
        if img.data is None: return True
    return False

def render(*args, dpi=128, onload=None, renderer=CodeCogs, wait=0.2):
    dpi = "\\dpi{" + str(dpi) + "}"
    imgs = [renderer(dpi + latex, onload) for latex in args]
    for img in imgs: img.start()
    while _waiting(imgs): sleep(wait)
    imgs = [img.data for img in imgs]
    return imgs if len(imgs) > 1 else imgs[0]
