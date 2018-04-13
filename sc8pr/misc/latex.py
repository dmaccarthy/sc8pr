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

    def __init__(self, latex, raw, onload):
        self.url = self._url + quote(latex)
        self.onload = raw, onload
        super().__init__()

    def run(self):
        data = urlopen(self.url).read()
        raw, onload = self.onload
        if not raw: data = pygame.image.load(BytesIO(data), "x.png")
        self.data = onload(data) if onload else data


def _waiting(imgs):
    "Check whether there are responses pending"
    for img in imgs:
        if img.data is None: return True
    return False

def render(*args, **kwargs):
    dpi = "\\dpi{" + str(kwargs.get("dpi", 128)) + "}"
    imgs = [CodeCogs(dpi + latex, kwargs.get("raw"), kwargs.get("onload"))
        for latex in args]
    for img in imgs: img.start()
    while _waiting(imgs): sleep(0.002)
    imgs = [img.data for img in imgs]
    return imgs[0] if len(imgs) == 1 else imgs
