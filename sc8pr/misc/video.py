# Copyright 2015-2017 D.G. MacCarthy <http://dmaccarthy.github.io>
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
from os.path import isfile
from sc8pr import Image, BaseSprite
from sc8pr.sprite import Sprite
from sc8pr.util import hasAlpha, surfaceData
from struct import unpack
from json import loads, dumps


class Video(Sprite):
    "A class for storing and retrieving sequences of compressed images"

    _costumes = []
    _current = None,

    def __init__(self, data=None, alpha=True, notify=False):
        self.alpha = alpha
        self.meta = {}
        t = type(data)
        if t is str: self._load(data, notify)
        elif t is tuple and type(data[0]) is int: self._size = data[0]
        elif data:
            self._costumes = [surfaceData(img) for img in data]
        if len(self._costumes):
            img = Image(*self._costumes[0])
            self._size = img.size
            self._current = 0, img

    def __len__(self): return len(self._costumes)

    def _loadMeta(self, zf):
        try:
            meta = loads(str(zf.read("meta.json"), encoding="utf8"))
            if meta:
                for k in meta:
                    self.meta[k] = zf.read(k)
        except: pass

    def _saveMeta(self, zf):
        if self.meta:
            keys = list(self.meta.keys())
            zf.writestr("meta.json", dumps(keys))
            for k in keys:
                data = self.meta[k]
                if type(data) not in (str, bytes): data = str(data)
                if type(data) is str: data = bytes(data, encoding="utf8")
                zf.writestr(k, data)

    def _load(self, fn, notify=False):
        "Load the video from a ZIP file"
        with ZipFile(fn) as zf:
            self._loadMeta(zf)
            self._costumes = []
            i = 0
            while i >= 0:
                try:
                    data = zf.read(str(i))
                    data = data[:-12], data[-12:]
                    i += 1
                    self._costumes.append(data)
                    if notify: notify(fn, i, self)
                except:
                    if notify: notify(fn, None, self)
                    i = -1
        try: # Adjust for duplicated frames
            cs = unpack("!{:d}B".format(len(self._costumes)), self.meta["repeat"])
            i = 0
            for repeat in cs:
                if repeat:
                    frame = self._costumes[i]
                    self._costumes = self._costumes[:i] + [frame for n in range(repeat)] + self._costumes[i:]
                i += 1 + repeat
        except: pass

    def costume(self):
        "Return an Image instance of the current costume"
        n = self.costumeNumber
        if n != self._current[0]:
            self._current = n, Image(*self._costumes[n])
        img = self._current[1]
        srf = img.image
        if self.alpha and not hasAlpha(srf):
            img = Image(srf.convert_alpha())
            self._current = n, img
        return img.config(size=self.size, angle=self.angle)

    def __iadd__(self, img):
        "Append a frame to the video"
        self._costumes.append(surfaceData(img))
        return self

    append = __iadd__

    def extend(self, imgs):
        "Append multiple frames to the video"
        self._costumes.append([surfaceData(img) for img in imgs])
        return self

    def clip(self, start=0, end=None):
        "Extract a continuous sequence of frames as a new Video instance"
        vid = Video(alpha=self.alpha)
        vid._size = self.size
        costumes = self._costumes
        if end is None: end = len(costumes)
        vid._costumes = costumes[start:end]
        return vid

    def save(self, fn, notify=False):
        "Save the video as a ZIP file"
        with ZipFile(fn, "w") as zf:
            self._saveMeta(zf)
            costumes = self._costumes
            for i in range(len(costumes)):
                data, mode = costumes[i]
                zf.writestr(str(i), data + mode)
                if notify: notify(fn, i + 1, self)
        if notify: notify(fn, None, self)

    def exportFrames(self, fn="save/frame{:05d}.png", notify=False):
        "Save the video as a sequence of individual frames"
        costumes = self._costumes
        for i in range(len(costumes)):
            Image(*costumes[i]).save(fn.format(i))
            if notify: notify(fn, i + 1, self)
        if notify: notify(fn, None, self)

    @staticmethod
    def importFrames(fn, seq=0, alpha=True, notify=False):
        "Load the video from a sequence of individual frames"
        if type(seq) is int:
            seq = range(seq, _lastFile(fn, seq) + 1)
        vid = Video(alpha=alpha)
        n = 0
        for s in seq:
            img = Image(fn.format(s))
            vid += img
            n += 1
            if notify: notify(fn, n, vid)
        img = Image(*vid._costumes[0])
        vid._size = img.size
        vid._current = 0, img
        if notify: notify(fn, None, vid)
        return vid

    def capture(self, sk):
        "Capture the current frame of the sketch"
        try: n = self.interval
        except: self.interval = n = 1
        if sk.frameCount % n == 0: self += sk.image


def _lastFile(fn, start=0, jump=512):
    "Determine the last file in a numbered sequence"
    end = jump
    while isfile(fn.format(end)): end += jump
    start = end - jump
    while end > start + 1:
        n = (end + start) // 2
        if isfile(fn.format(n)): start = n
        else: end = n
    if end > start: return end if isfile(fn.format(end)) else start 
    else: return start


class VideoSprite(Video, BaseSprite): pass
