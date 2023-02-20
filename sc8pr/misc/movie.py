# Copyright 2015-2023 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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


from sc8pr.misc.video import Video, FFReader


class Movie(Video):

    def __init__(self, src, skip=0, frames=None, alpha=False, **kwargs):
        self._alpha = alpha
        self._skip = skip
        self._frames = frames
        self._reader = lambda: FFReader(src, **kwargs)
        self._size = kwargs.get("size", None)
        self.restart()

    def restart(self):
        try: self._vid.close()
        except: pass
        self._vid = self._reader().skip(self._skip)
        self._read = (lambda r: next(r).rgba) if self._alpha else (lambda r: next(r).img)
        self._costumeNumber = 0
        self._costume = self._read(self._vid)
        if self._size is None: self._size = self._costume.size
        return self

    @property
    def costumeNumber(self): return self._costumeNumber
 
    @costumeNumber.setter
    def costumeNumber(self, n):
        self._costumeNumber += 1
        if n != self._costumeNumber:
            raise ValueError("movie frames must be read in order")
        try:
            if n == self._frames: raise StopIteration()
            self._costume = self._read(self._vid)
        except StopIteration:
            if self._frames is None or n < self._frames:
                self._frames = n
            self.restart()

    def close(self): self.reader.close()

    @property
    def clip(self):
        s = self._skip
        n = self._vid._meta.get("nframes")
        if n == float("inf"): n = None
        f = self._frames
        if f is None: f = n
        else:
            try:
                f += s
                if n and n < f: f = n
            except: f = None
        return s, f

    def __len__(self):
        try:
            a, b = self.clip
            b -= a
        except: b = 0
        return b
