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


from sc8pr.misc.s8v import S8Vfile
from sc8pr import Image, PixelData, version
from sc8pr.sprite import Sprite
from sc8pr.util import hasAlpha, fileExt
from time import time

def _indx(obj, i):
    "Correct negative/omitted frame index"
    n = len(obj)
    if i is None: i = n
    elif i < 0: i += n
    return i


class Video(Sprite):
    "A class for storing and retrieving sequences of compressed images"
#     _autoSave = False
    _paused = False
    frameTimes = None

    def __init__(self, data=None, alpha=False, progress=None, start=0, end=None):
        self.purge()
        self.alpha = alpha
        self.meta = {}
        t = type(data)
        if t is str: self._load(data, progress, start, end)
        elif t is tuple and type(data[0]) is int: self._size = data
        elif data:
            self._costumes = [PixelData(img, True) for img in data]
        if len(self._costumes):
            img = self._costumes[0].img
            self._size = img.size
            self._current = 0, img

    def _load(self, fn, progress=None, start=0, end=None):
        "Load the video from a S8V file"
        with S8Vfile(fn) as s8v:
            self.meta = s8v.meta
            i = 0
            for f in s8v.clip(start, end):
                self._costumes.append(f)
                if progress:
                    i += 1
                    progress(i, s8v.frames)

    def save(self, fn, progress=None, append=False):
        "Save the Video as an S8V archive of PixelData binaries"
        fn = fileExt(fn, ["s8v", "zip"])
        with S8Vfile(fn, "a" if append else "w", **self.meta) as s8v:
            i = 0
            n = len(self._costumes)
            for c in self._costumes:
                s8v.append(c)
                if progress:
                    i += 1
                    progress(i, n)
        return self

    def purge(self):
        "Remove all frames from the video"
        self._costumes = []
        self._current = None,
        return self

    def __len__(self): return len(self._costumes)

    def __iadd__(self, img):
        "Append a frame to the video"
        if isinstance(img, Video): return self.extend(img._costumes)
        if not isinstance(img, PixelData):
            if type(img[0]) is not bytes:
                img = bytes(img[0]), img[1]
            img = PixelData(img, True)
        self._costumes.append(img)
        if not hasattr(self, "_size"): self._size = img.size
#         if self._autoSave:
#             n = len(self)
#             if n > self._autoSave: self.autoSave(True, n)
        return self

    def __add__(self, other):
        "Concatenate another video"
        c = self.clip()
        c += other
        return c

    def __getitem__(self, n):
        "Return a frame as an Image instance, or a slice as a new Video instance"
        if type(n) is slice:
            r = range(n.start, n.stop, n.step) if n.step else range(n.start, n.stop)
            return self.clip(r)
        if n != self._current[0]:
            self._current = n, self._costumes[n].img
        img = self._current[1]
        srf = img.original
        if self.alpha and not hasAlpha(srf):
            img = Image(srf.convert_alpha())
            self._current = n, img
        return img.config(size=self.size, angle=self.angle)

    def splice(self, i, n=0, vid=[]):
        "Insert and/or remove a clip"
        if not isinstance(vid, Video): vid = Video(vid)
        i = _indx(self, i)
        c = self._costumes
        if i == len(c): self += vid
        else:
            c[i:i+n] = vid._costumes
            if not hasattr(self, "_size") and len(self):
                self._size = c[0].size
        return self

    def effect(self, effect, out=False):
        "Apply a transition effect to a Video and return a new Video instance"
        dest = Video()
        n = len(self)
        dn = 1 / n
        if out:
            n = 1 - dn
            dn = -dn
        else: n = 0
        for frame in self:
            dest += effect.apply(frame, n)
            n += dn
        return dest

    def effectInPlace(self, effect, start=0, end=None, out=False):
        "Apply a transition effect in place"
        start = _indx(self, start)
        end = _indx(self, end)
        vid = self.clip(start, end).effect(effect, out)
        self.splice(start, len(vid), vid)
        return self

#     def autoSave(self, fn=True, size=None):
#         "Turn auto save on/off, or perform an auto save"
#         if fn is True:
#             if size is None: size = len(self)
#             if size:
#                 self.save(self._savefile, append=self._append)
#                 self.purge()._append += size
#         elif fn is False: self._autoSave = False
#         else:
#             self._autoSave = size if size else 4096
#             self._savefile = fn
#             self._append = 0
#         return self

    def frame(self, n):
        "Return a frame as a PixelData instance"
        return self._costumes[n]

    def frames(self):
        "Generate a sequence of frames as PixelData"
        for f in self._costumes: yield f

    def costume(self):
        "Return the current costume"
        return self[self.costumeNumber]

    def play(self, t=None):
        "Pause or resume playback"
        if t or t is None and not self.costumeTime:
            self.costumeTime = t if t else self._paused
            self._paused = False
        elif self.costumeTime:
            self._paused = self.costumeTime 
            self.costumeTime = 0
        return self

    def extend(self, imgs):
        "Append multiple frames to the video"
        for img in imgs: self += img
        return self

    @staticmethod
    def _iter(fn, maxFrames=256):
        "Iterate through the frames in an s8V file"
        i = 0
        vid = Video(fn, start=i, end=i+maxFrames)
        while len(vid):
            for f in vid.frames(): yield f
            i += maxFrames
            vid = Video(fn, start=i, end=i+maxFrames)
    
    def costumeSequence(self, seq):
        msg = "In-place costume sequencing is not supported; use the clip method instead"
        raise NotImplementedError(msg)

    def clip(self, start=0, end=None):
        "Extract a sequence of frames as a new Video instance"
        vid = Video(alpha=self.alpha)
        vid._size = self.size
        costumes = self._costumes
        if type(start) is int:
            start = _indx(self, start)
            end = _indx(self, end)
            start = range(start, end, 1 if end > start else -1)
        vid._costumes = [costumes[_indx(self, i)] for i in start]
        vid.meta = dict(self.meta)
        return vid

    def capture(self, sk):
        "Capture the current frame of the sketch"
#         try: n = self.interval
#         except: self.interval = n = 1
#         if sk.frameCount % n == 0:
        self += sk
        if self.frameTimes is not None:
            t = time()
            if len(self.frameTimes) == 0: self._start = t
            self.frameTimes.append(t - self._start)

    def sync(self, fps=30, original=None):
        "Use frameTimes data to correct for dropped frames"
        vid = Video().config(_size=self.size)
        vid.meta["frameRate"] = fps
        if original is None and self.frameTimes:
            ft = self.frameTimes
        else:
            if original is None: original = self.meta.get("frameRate", 30)
            ft = [n/original for n in range(len(self))]
        for f in range(len(ft)):
            i = round(fps * ft[f])
            for n in range(1 + i - len(vid)):
                vid._costumes.append(self._costumes[f])
        return vid

    def scaleFrames(self, size=None, inPlace=False):
        "Ensure all frame images have the same size"
        if not size: size = self.size
        if inPlace: vid = self
        else:
            vid = Video().config(size=size)
            fps = self.meta.get("frameRate")
            if fps: vid.meta["frameRate"] = fps
        for i in range(len(self)):
            px = self._costumes[i]
            if px.size != size:
                px = PixelData(px.img.config(size=size).image, True)
                if inPlace: self._costumes[i] = px
            if not inPlace: vid._costumes.append(px)
        return vid

    def removeGaps(self, gap, repl):
        "Remove large gaps between frame times"
        data = self.frameTimes
        n = len(data)
        for i in range(1, n):
            x = data[i] - data[i-1]
            if x > gap:
                dt = x - repl
                for j in range(i, n): data[j] -= dt
        return self

    def convert_alpha(self):
        "Convert frames to RGBA"
        i = 0
        for v in self._costumes:
            self._costumes[i] = PixelData(v.srf.convert_alpha(), True)
            i += 1
        return self
