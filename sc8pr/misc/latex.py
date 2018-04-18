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

"Render LaTeX markup as PNG images using codecogs.com"

from threading import Thread
from io import BytesIO
from time import sleep
from urllib.request import urlopen
from urllib.parse import quote
from os.path import abspath, isdir, isfile
from random import choice
import json
try:
    import pygame
    usePygame = True
except:
    usePygame = False

CHARS = "abcdefghijklmnopqrstuvwxyz"

def vec(latex):
    "Compose LaTeX markup for a vector"
    return "{\\vec{\\mathbf " + latex + "}}"

def latexColor(latex, color):
    "Compose LaTeX for colored rendering"
    return "{\\color{" + color + "}" + latex + "}"

def _loadImage(data):
    """Create a pygame.Surface from a filename or PNG bytes data;
    if usePygame is False, the image will be returned as a
    PNG-encoded bytes object."""
    t = type(data)
    if usePygame:
        if t is bytes: data = BytesIO(data)
        data = (pygame.image.load(data) if t is str
            else pygame.image.load(data, "x.png"))
    else:
        if t is str:
            with open(data, "rb") as f: data = f.read()
    return data


class CodeCogsRequest(Thread):
    "Send request to codecogs.com in a separate thread"
    data = None
    _url = "https://latex.codecogs.com/png.latex?"

    def __init__(self, latex, raw, onload):
        super().__init__()
        self.url = self._url + quote(latex)
        self.onload = raw, onload

    def run(self):
        try: data = urlopen(self.url).read()
        except Exception as e: data = e
        raw, onload = self.onload
        if not raw: data = _loadImage(data)
        self.data = onload(data) if onload else data

    @staticmethod
    def waiting(imgs):
        "Check whether there are responses pending"
        w = False
        for img in imgs:
            data = img.data
            if isinstance(data, Exception): raise(data)
            if data is None: w = True
        return w

    @staticmethod
    def wait(imgs):
        "Wait until all image responses are received"
        while CodeCogsRequest.waiting(imgs): sleep(0.002)

    @staticmethod
    def request(*args, **kwargs):
        "Create a CodeCogsRequest instance for each request"
        dpi = kwargs.get("dpi", 128)
        if dpi:
            dpi = dpi = "\\dpi{" + str(dpi) + "}"
            latex = lambda x: dpi + x
        else: latex = lambda x: x
        imgs = [CodeCogsRequest(latex(x), kwargs.get("raw"),
            kwargs.get("onload")) for x in args]
        for img in imgs: img.start()
        return imgs


class LatexCache:
    "Render LaTeX markup using codecogs.com and a local cache folder"

    def __init__(self, folder="./"):
        folder = abspath(folder)
        if not isdir(folder): raise NotADirectoryError()
        self.path = folder
        try:
            with open(self.indexFile, encoding="utf-8") as f:
                self.index = json.load(f)
        except: self.index = {}

    def _alias(self, n=8):
        "Generate random alias"
        return "".join(choice(CHARS) for i in range(n))

    def latex(self, alias):
        "Look up LaTeX markup for the given alias"
        for k, v in self.index.items():
            if v == alias: return k

    def update(self):
        "Save index as JSON file"
        with open(self.indexFile, "w", encoding="utf-8") as f: 
            json.dump(self.index, f, ensure_ascii=False)

    def file(self, name):
        return abspath(self.path + "/" + name)

    @property
    def indexFile(self): return self.file("index.json")

    def png(self, alias, dpi=128):
        return self.file("l8x{}_{}.png".format(dpi, alias))

    def cached(self, alias, dpi=128):
        "Check if file exists in cache"
        return isfile(self.png(alias, dpi)) if alias else False

    def get(self, *args, dpi=128, update=True, onload=None, color=None):
        "Return rendered LaTeX as an Image or list of Image instances"

        # Determine which files exist in cache
        imgs = []
        cogs = []
        for latex in args:
            if color: latex = latexColor(latex, color)
            alias = self.index.get(latex)
            if alias and self.cached(alias, dpi):
                imgs.append(self.png(alias, dpi))
            else:
                imgs.append(None)
                cogs.append(latex)

        # Send requests to codecogs.com
        if cogs: cogs_img = CodeCogsRequest.request(*cogs, dpi=dpi, raw=True)

        # Load images from cache
        for i in range(len(imgs)):
            fn = imgs[i]
            if fn: imgs[i] = _loadImage(fn)

        # Process cogecogs.com responses
        if cogs:
            aliasList = list(self.index.values())
            CodeCogsRequest.wait(cogs_img)
            for i in range(len(cogs)):
                latex = cogs[i]
                alias = self.index.get(latex)
                if alias is None:
                    while alias is None or alias in aliasList:
                        alias = self._alias()
                    self.index[latex] = alias
                    aliasList.append(alias)
                fn = self.png(alias, dpi)
                data = cogs_img[i].data
                with open(fn, "wb") as png: png.write(data)
                imgs[imgs.index(None)] = _loadImage(data)
            if update: self.update()

        if onload: imgs = [onload(f) for f in imgs]
        return imgs[0] if len(imgs) == 1 else imgs


def render(*args, **kwargs):
    "Render one or more LaTeX expressions without caching"
    imgs = CodeCogsRequest.request(*args, **kwargs)
    CodeCogsRequest.wait(imgs)
    imgs = [img.data for img in imgs]
    return imgs[0] if len(imgs) == 1 else imgs
