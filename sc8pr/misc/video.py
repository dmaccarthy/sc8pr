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

from sc8pr import Image, BaseSprite, logError
from sc8pr.util import surface, scale
from sc8pr.sprite import CostumeImage, Sprite
from zipfile import ZipFile, ZIP_DEFLATED
from json import dumps, loads

RGB = 24
RGBA = 32
_open_list = []


class Video(ZipFile, CostumeImage):
    "Sprites associated with a ZIP archive video"

    @staticmethod
    def closeAll():
        for v in list(_open_list): v.close()

    def __init__(self, zfile, **kwargs):
        self._open(zfile, **kwargs)
        try:
            self._size = tuple(self.meta["size"])
            self._info = self._size, "RGBA" if self.meta["bits"] == 32 else "RGB"
            self._costume = self[0]
        except:
            self._costume = self._size = None

    def __len__(self):
        s = self._seq
        return len(s) if s else self._nframes

    @property
    def costumeList(self): return self

    @property
    def fps(self): return self._meta.get("fps", 30)

    @property
    def costumeNumber(self): return self._costumeNumber
 
    @costumeNumber.setter
    def costumeNumber(self, n):
        s = self._seq
        self._costumeNumber = n = n % len(self)
        self._costume = self[s[n] if s else n].rgba

    def costume(self):
        "Return an Image instance of the current costume"
        return self._costume.config(size=self._size, angle=self.angle)

    def clip(self, zfile, mode="x", start=0, frames=None):
        m = self.meta
        with Video(zfile, mode=mode) as zo:
            clip = self[start:start+frames] if frames else self[start:]
            for f in clip: zo.write(f)
            zo.meta.update(m)
            try: del zo.meta["duration"]
            except: pass
        return self


# ZipFile reading and writing...

    write_alpha = read_alpha = None

    def _open(self, zfile, mode="r", **kwargs):
        "Open the ZipFile and extract metadata"
        attr = {"compression": ZIP_DEFLATED} if mode in ("w", "x") else {}
        attr.update(kwargs)
        super().__init__(zfile, mode, **attr)
        _open_list.append(self)
        try: meta = loads(self.read("meta.json"))
        except: meta = {"nframes": 0}
        self._meta = meta
        self._nframes = meta["nframes"]
        self._readN = self._readImg = self._append = None

    def close(self, *args):
        try: # May fail if file is read-only
            if self._nframes != self._meta["nframes"]:
                self._meta["nframes"] = self._nframes
                self.writestr("meta.json", dumps(self._meta))
        except: pass
        super().close()
        if self in _open_list: _open_list.remove(self)

    __exit__ = close

    @property
    def meta(self): return self._meta

    def _actual(self, n):
        "Get the actual ZipFile key for the requested frame"
        if n < 0: n += self._nframes
        if n < 0 or n >= self._nframes: return None
        data = None
        while n >= 0 and data is None:
            try:
                self.getinfo(str(n))
                data = n
            except: n -= 1
        return data

    def _get_slice(self, start, stop, step=1):
        "Generate Image instances for requested slice"
        n = self._nframes
        if start is None: start = 0
        elif start < 0: start += n
        if stop is None: stop = self._nframes
        elif stop < 0: stop += n
        for i in range(start, stop, step): yield self[i]

    def __getitem__(self, i):
        "Return an Image or generator for the requested index or slice"
        if type(i) is slice: return self._get_slice(i.start, i.stop, i.step if i.step else 1)
        i = self._actual(i)
        if i is None: raise IndexError("out of range")
        if i != self._readN:
            self._readN = 1
            img = Image.fromBytes((self.read(str(i)), self._info)).convert(self.read_alpha)
            self._readImg = img
        return self._readImg

    def write(self, *args, repeat=1):
        "Write images to the ZipFile"
        alpha = self.write_alpha
        for img in args:
            img = surface(img)
            if self._nframes == 0:
                self.meta["size"] = img.get_size()
                self.meta["bits"] = img.get_bitsize() if alpha is None else 32 if alpha else 24
            size = self.meta["size"]
            if img.get_size() != size:
                img = scale(img, size)
            data = Image(img).convert(alpha).bytesTuple(False)
            if self._append is None or data != self._append: 
                self._append = data
                self.writestr(str(self._nframes), data)
            self._nframes += repeat
        return self

    __iadd__ = write


class VideoSprite(Video, BaseSprite):
    update = Sprite.update
