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


from zipfile import ZipFile
from json import loads, dumps
from sc8pr import PixelData, version
  

class S8Vfile:
    "Read and append compressed PixelData binary data to an S8V ZipFile"

    @staticmethod
    def info(fn):
        with ZipFile(fn, "r") as zf:
            try: meta = loads(str(zf.read("metadata"), encoding="utf-8"))
            except: meta = {}
        return meta

    def __init__(self, fn, mode="r", **meta):
        self._zf = ZipFile(fn, mode)
        self.frames = 0
        try:
            data = self._zf.read("metadata")
            self.meta = loads(str(data, encoding="utf-8"))
        except:
            metadata = {"Saved By": "sc8pr{}".format(version)}
            metadata.update(meta)
            self.meta = metadata
            data = bytes(dumps(metadata, ensure_ascii=False), encoding="utf-8")
            self._zf.writestr("metadata", data)
        names = self._zf.namelist()
        for name in names:
            try:
                name = int(name)
                self.frames += 1
            except: pass
        self._last = bytes(self.read(self.frames - 1)) if self.frames else None

    def append(self, data):
        "Append a PixelData instance to the file"
        if type(data) is PixelData: data.compress()
        else: data = PixelData(data, True)
        data = bytes(data)
        if data == self._last: data = b""
        else: self._last = data
        self._zf.writestr(str(self.frames), data)
        self.frames += 1

    def read(self, frame, allowEmpty=False, compress=True):
        "Read one frame as a compressed PixelData instance"
        data = self._zf.read(str(frame))
        if not allowEmpty:
            while not data:
                data = self._zf.read(str(frame))
                frame -= 1
        return PixelData(data, compress) if data else None

    def clip(self, start=0, end=None):
        "Generate a sequence of consecutive frames as PixelData instances"
        last = None
        for i in range(start, end if end else self.frames):
            pxd = self.read(i, True)
            if pxd: last = pxd
            else: pxd = last
            yield pxd

    def __enter__(self): return self
    def __exit__(self, *args): self._zf.close()
    close = __exit__
    capture = append
