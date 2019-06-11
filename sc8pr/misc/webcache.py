# Copyright 2015-2019 D.G. MacCarthy <http://dmaccarthy.github.io>
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

"Retrieve data asynchronously from the web, and save the data in a cache folder"

from threading import Thread
from io import BytesIO
from time import sleep
from urllib.request import urlopen
from urllib.parse import quote, urlparse
from os.path import abspath, isdir, isfile
from random import randint
import pygame
from sc8pr.util import fileExt

def _fname(p):
    "Get file name"
    return urlparse(p).path.replace("\\", "/").split("/")[-1]

def _fext(p):
    "Get file extension"
    p = _fname(p).split(".")
    return p[-1] if len(p) > 1 else ""

def wrap(latex, val, key="color"):
    "Wrap LaTeX markup in a color or similar modifier"
    return "{" + pref(latex, val, key) + "}"

def pref(latex, val, key="dpi"):
    "Prefix LaTeX markup with a dpi or similar modifier"
    return "\\" + key + "{" + str(val) + "}" + latex


LATEX_URL = "https://latex.codecogs.com/png.latex?{}"
LATEX_FMT = "png"

def latex_url(latex, dpi, color):
    if color: latex = wrap(latex, color)
    key = pref(latex, dpi)
    return key, LATEX_URL.format(quote(key))


class WebRequest(Thread):
    "Thread for sending HTTP requests and processing responses "
    response = None
    success = error = None

    def __init__(self, url, image=None, save=None):
        super().__init__()
        self.data = None
        self.url = url
        self.save = save
        if image is True:
            save = _fext(save)
            image = save if save else _fext(url)
        self._image = image

    def _convertImage(self, data):
        "Convert response data from bytes to pygame.Surface"
        image = self._image
        if image:
            hint = "x." + image
            data = pygame.image.load(BytesIO(data), hint)
        return data          

    def onload(self):
        "Callback when request completed"
        d = self.data
        if isinstance(d, Exception):
            if self.error: self.error(self)
        elif self.success: self.success(self)

    def run(self):
        try:
            if WebCache.log: WebCache.log("Requesting:", self.url)
            self.response = r = urlopen(self.url)
            data = r.read()
            if self.save:
                if WebCache.log: WebCache.log("Saving:", self.save)
                with open(self.save, "wb") as f: f.write(data)
            self.data = self._convertImage(data)
        except Exception as e: self.data = e
        self.onload()

    def wait(self):
        while self.data is None: sleep(0.001)
        return self


class CacheRequest(WebRequest):
    "Thread for loading cached data asynchronously"

    def __init__(self, url, image, save):
        Thread.__init__(self)
        self.url = url
        self.save = save
        self.data = None
        self._image = image

    def run(self):
        save = self.save
        if WebCache.log: WebCache.log("Loading:", save)
        try:
            if self._image: self.data = pygame.image.load(save)
            else:
                with open(save, "rb") as f: self.data = f.read()
        except Exception as e: self.data = e
        self.onload()


class WebCache:
    "Fetch and cache web resources asynchronously"
    log = None
    _IMGS = "png", "jpg", "jpeg", "jpe", "gif", "bmp", "tif", "tiff", "tga", "pcx"

    def __init__(self, folder="./"):
        folder = abspath(folder)
        if not isdir(folder): raise NotADirectoryError()
        self._queue = []
        self.path = folder
        self.index = {}
        self.imageData(False)
        try:
            with open(self._indexFile, encoding="utf-8") as f:
                if self.log: self.log("Reading index file")
                isKey = True
                for line in f:
                    if isKey: key = line.strip()
                    else: self._setkey(key, line.strip(), False)
                    isKey = not isKey
        except: pass

    def __getitem__(self, i):
        if i < 0: i += len(self._queue)
        return self._queue[i]
    
    def __len__(self): return len(self._queue)

    def _file(self, name): return abspath(self.path + "/" + name)

    @property
    def _indexFile(self): return self._file("webcache_index.txt")

    def imageData(self, dataType=True, formats=True):
        "Specify which file extension to convert to pygame.Surface; optional subsequent callback"
        if not dataType or dataType is bytes:
            self._pySrf = None
            self._imgExt = ()
        else:
            if pygame and dataType is pygame.Surface: dataType = True
            self._pySrf = dataType
            if formats is True: self._imgExt = self._IMGS
            else: self._imgExt = formats
        return self

    def get(self, key, filename=None, dpi=None, color=None, success=None, error=None):
        "Push one request thread onto the queue"

        # Get URL and save name
        if dpi: # Render LaTeX using codecogs.com
            key, url = latex_url(key, dpi, color)
            if filename in (None, True): filename = self._randName(LATEX_FMT)
        else:
            url = key
            if filename is True: filename = _fname(url)
            elif filename is None: filename = self._randName(_fext(url))
        filename = filename.replace("\\", "/").split("/")[-1]
        if isfile(self._file(filename)) and (url, filename) not in self.index.items():
            if self.log: self.log("File name conflict: {} -> ".format(filename), end="")
            filename = self._randName(_fext(filename))
            if self.log: self.log(filename)

        # Load from cache
        r = None
        prevSave = self.index.get(key)
        if prevSave:
            prevSave = self._file(prevSave)
            if isfile(prevSave):
                r = CacheRequest(url, _fext(filename) in self._imgExt, prevSave)

        # Load via HTTP request
        if not r:
            self._setkey(key, filename)
            with open(self._indexFile, "a", encoding="utf-8") as f:
                for b in (key, "\n", filename, "\n"): f.write(b)
            r = WebRequest(url, _fext(filename) in self._imgExt, self._file(filename))

        # Send request
        r.success = success
        r.error = error
        self._queue.append(r)
        r.start()
        return r

    def _setkey(self, key, val, log=True):
        "Add item to index after removing conflicting entries"
        if log and self.log: self.log("Updating index")
        absSave = self._file(val)
        dupl = []
        for k, v in self.index.items():
            if self._file(v) == absSave: dupl.append(k)
        for k in dupl: del self.index[k]
        self.index[key] = val

    def wait(self):
        "Wait for all requests to finish"
        for r in self._queue: r.wait()
        return self

    def error(self, ignorePending=False):
        "Check if any exceptions occurred"
        wait = not ignorePending
        for r in self._queue:
            if wait: r.wait()
            if isinstance(r.data, Exception): return r

    @property
    def status(self):
        s = e = p = 0
        for r in self._queue:
            if r.data is None: p += 1
            elif isinstance(r.data, Exception): e += 1
            else: s += 1
        return dict(success=s, error=e, pending=p)

    def flush(self):
        "Reset queue and return generator for response data"
        q = self._queue
        self._queue = []
        return self._iter(q, self._pySrf)

    @staticmethod
    def _iter(q, cb):
        "Iterate through response data"
        for item in q:
            item = item.wait().data
            try:
                if cb and isinstance(item, pygame.Surface): item = cb(item)
            except: pass
            yield item

    def _randName(self, ext=None):
        "Create a random file name"
        a = None
        v = self.index.values()
        letter = lambda: chr(ord('a') + randint(0, 25))
        while not a or a in v:
            a = "".join(letter() for i in range(8))
            if ext is not None: a = fileExt(a, ext)
        return a

    def tidy(self):
        "Remove deleted/missing files from cache index"
        index = self.index
        for key, val in list(index.items()):
            filename = self._file(val)
            if not isfile(filename): del index[key]
        index = self.index
        with open(self._indexFile, "w", encoding="utf-8") as f:
            if self.log: self.log("Saving index")
            for key in index:
                for b in (key, "\n", index[key], "\n"): f.write(b)
