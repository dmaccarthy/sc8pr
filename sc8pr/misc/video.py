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
from json import loads, dumps
from os.path import isfile
from sc8pr import Image, version
from sc8pr.sprite import Sprite
from sc8pr.util import hasAlpha, surfaceData


def jsonToBytes(obj):
    return bytes(dumps(obj, ensure_ascii=False), encoding="utf8")

def jsonFromBytes(b):
    return loads(str(b, encoding="utf8"))


class Video(Sprite):
    "A class for storing and retrieving sequences of compressed images"
    _current = None,

    def __init__(self, data=None, alpha=True, notify=False):
        self.alpha = alpha
        self.meta = {}
        self._costumes = []
        t = type(data)
        if t is str: self._load(data, notify)
        elif t is tuple and type(data[0]) is int: self._size = data#[0]
        elif data:
            self._costumes = [surfaceData(img) for img in data]
        if len(self._costumes):
            img = Image(*self._costumes[0])
            self._size = img.size
            self._current = 0, img

    def __len__(self): return len(self._costumes)

    def __iadd__(self, img):
        "Append a frame to the video"
        self._costumes.append(surfaceData(img))
        return self

    append = __iadd__

    def __getitem__(self, n):
        "Return a frame as an Image instance"
        if n != self._current[0]:
            self._current = n, Image(*self._costumes[n])
        img = self._current[1]
        srf = img.original #img.image
        if self.alpha and not hasAlpha(srf):
            img = Image(srf.convert_alpha())
            self._current = n, img
        return img.config(size=self.size, angle=self.angle)

    def costume(self):
        "Return the current costume"
        return self[self.costumeNumber]

    def extend(self, imgs):
        "Append multiple frames to the video"
        self._costumes.append([surfaceData(img) for img in imgs])
        return self

    def _loadMeta(self, zf):
        try: self.meta = jsonFromBytes(zf.read("metadata"))
        except: pass

    def _saveMeta(self, zf):
        if self.meta: zf.writestr("metadata", jsonToBytes(self.meta))

    def _load(self, fn, notify=False):
        "Load the video from a ZIP file"
        with ZipFile(fn) as zf:
            self._loadMeta(zf)
            self._costumes = []
            i = 0
            while i >= 0:
                try:
                    if notify: notify(fn, i, self)
                    data = zf.read(str(i))
                    if data: data = data[:-12], data[-12:]
                    else: data = self._costumes[i-1]
                    i += 1
                    self._costumes.append(data)
                except:
                    if notify: notify(fn, None, self)
                    i = -1

    def costumeSequence(self, seq):
        msg = "In-place costume sequencing is not supported; use the clip method instead"
        raise NotImplementedError(msg)

    def clip(self, start=0, end=None):
        "Extract a sequence of frames as a new Video instance"
        vid = Video(alpha=self.alpha)
        vid._size = self.size
        costumes = self._costumes
        if type(start) is int:
            if end is None: end = len(costumes)
            start = range(start, end, 1 if end > start else -1)
        vid._costumes = [costumes[i] for i in start]
        return vid

    def save(self, fn, notify=False):
        "Save the video as a ZIP file"
        self.meta["sc8pr.version"] = version
        with ZipFile(fn, "w") as zf:
            self._saveMeta(zf)
            costumes = self._costumes
            for i in range(len(costumes)):
                if notify: notify(fn, i, self)
                data, mode = costumes[i]
                zf.writestr(str(i), b'' if i and costumes[i] == costumes[i-1] else data + mode)
        if notify: notify(fn, None, self)

    def exportFrames(self, fn="save/frame{:05d}.png", notify=False):
        "Save the video as a sequence of individual frames"
        costumes = self._costumes
        for i in range(len(costumes)):
            if notify: notify(fn, i, self)
            Image(*costumes[i]).save(fn.format(i))
        if notify: notify(fn, None, self)

    @staticmethod
    def importFrames(fn, seq=0, alpha=True, notify=False):
        "Load the video from a sequence of individual frames"
        if type(seq) is int:
            seq = range(seq, _lastFile(fn, seq) + 1)
        vid = Video(alpha=alpha)
        n = 0
        for s in seq:
            if notify: notify(fn, n, vid)
            img = Image(fn.format(s))
            vid += img
            n += 1
        img = Image(*vid._costumes[0])
        vid._size = img.size
        vid._current = 0, img
        if notify: notify(fn, None, vid)
        return vid

    def capture(self, sk):
        "Capture the current frame of the sketch"
        try: n = self.interval
        except: self.interval = n = 1
        if sk.frameCount % n == 0: self += sk


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
