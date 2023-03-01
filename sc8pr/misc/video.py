# Copyright 2015-2023 D.G. MacCarthy <http://dmaccarthy.github.io>
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

from sc8pr import PixelData, Image, BaseSprite
from sc8pr.sprite import CostumeImage, Sprite
from zipfile import ZipFile, ZIP_DEFLATED
from json import dumps, loads


class VidZip:
    "A class for storing video frames in a ZIP archive"

    capture_RGB = True

    @property
    def meta(self): return self._meta

    def __enter__(self): return self
    def __len__(self): return self._nframes

    def __exit__(self, *args):
        try: # May fail if file is read-only
            if self._nframes != self._meta["nframes"]:
                self._meta["nframes"] = self._nframes
                self._zf.writestr("meta.json", dumps(self._meta))
        except: pass
        self._zf.close()

    close = __exit__

    def __init__(self, zfile, mode="r", **kwargs):
        attr = {"compression": ZIP_DEFLATED} if mode in ("w", "x") else {}
        attr.update(kwargs)
        self._zf = ZipFile(zfile, mode, **attr)
        try: meta = loads(self._zf.read("meta.json"))
        except: meta = {"nframes": 0}
        self._meta = meta
        self._nframes = meta["nframes"]
        self._readN = self._readPix = self._append = None

    def _actual(self, n):
        "Get the actual zipfile key for the requested frame"
        if n < 0: n += self._nframes
        if n < 0 or n >= self._nframes: return None
        data = None
        zf = self._zf
        while n >= 0 and data is None:
            try:
                zf.getinfo(str(n))
                data = n
            except: n -= 1
        return data

    def _get_slice(self, start, stop, step=1):
        "Generate PixelData instances for requested slice"
        n = self._nframes
        if start is None: start = 0
        elif start < 0: start += n
        if stop is None: stop = self._nframes
        elif stop < 0: stop += n
        for i in range(start, stop, step): yield self[i]

    def __getitem__(self, i):
        "Return a PixelData or generator for the requested index or slice"
        if type(i) is slice: return self._get_slice(i.start, i.stop, i.step if i.step else 1)
        i = self._actual(i)
        if i is None: raise IndexError("out of range")
        if i != self._readN:
            self._readN = 1
            self._readPix = PixelData(self._zf.read(str(i)))
        return self._readPix

    def write(self, *args, repeat=1):
        "Write images to the zipfile"
        for img in args:
            if not isinstance(img, PixelData):
                img = PixelData(img)
            if self.capture_RGB and img.mode == "RGBA":
                img = PixelData(img.srf.convert(24))
            img = bytes(img)
            if self._append is None or img != self._append: 
                self._append = img
                self._zf.writestr(str(self._nframes), img)
            self._nframes += repeat
        return self

    __iadd__ = write #capture          

    def clip(self, zfile, mode="x", start=0, frames=None):
        m = self.meta
        with VidZip(zfile, mode) as zo:
            clip = self[start:start+frames] if frames else self[start:]
            for f in clip: zo += f
            zo.meta.update(m)
            try: del zo.meta["duration"]
            except: pass
        return self


class Video(CostumeImage):
    "Sprites associated with a ZIP archive video"

    def __init__(self, zfile, alpha=False, **kwargs):
        self._vid = VidZip(zfile, **kwargs)  # Needs to be CLOSED!!
        self._costume = self._vid[0].rgba if alpha else self._vid[0].img
        self._size = self._costume.size

    def __len__(self):
        s = self._seq
        return len(s if s else self._vid)

    def close(self): self._vid._zf.close()

    @property
    def costumeList(self): return self._vid

    @property
    def fps(self): return self._vid._meta.get("fps", 30)

    @property
    def costumeNumber(self): return self._costumeNumber
 
    @costumeNumber.setter
    def costumeNumber(self, n):
        s = self._seq
        self._costumeNumber = n = n % len(s if s else self._vid)
        self._costume = self._vid[s[n] if s else n].rgba

    def costume(self):
        "Return an Image instance of the current costume"
        return self._costume.config(size=self._size, angle=self.angle)


class VideoSprite(Video, BaseSprite):
    update = Sprite.update
