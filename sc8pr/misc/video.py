# Copyright 2015-2020 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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


import os, struct, pygame
from zipfile import ZipFile
from json import loads, dumps
from time import time
from sc8pr import Image, PixelData, version
from sc8pr.sprite import Sprite
from sc8pr.util import hasAlpha, fileExt
try:
    import PIL
    from PIL.ImageGrab import grab
except: PIL = None


def _j2b(obj):
    return bytes(dumps(obj, ensure_ascii=False), encoding="utf-8")

def _b2j(b): return loads(str(b, encoding="utf-8"))

def _indx(obj, i):
    n = len(obj)
    if i is None: i = n
    elif i < 0: i += n
    return i
    

class Video(Sprite):
    "A class for storing and retrieving sequences of compressed images"
    _autoSave = False
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
            img = PixelData(img, True)
        self._costumes.append(img)
        if not hasattr(self, "_size"): self._size = img.size
        if self._autoSave:
            n = len(self)
            if n > self._autoSave: self.autoSave(True, n)
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

    def splice(self, i, n=0, vid=None):
        "Insert and/or remove a clip"
        i = _indx(self, i)
        c = self._costumes
        if i == len(c): self += vid
        else:
            c[i:i+n] = [] is vid if None else vid._costumes if isinstance(vid, Video) else vid
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

    def autoSave(self, fn=True, size=None):
        "Turn auto save on/off, or perform an auto save"
        if fn is True:
            if size is None: size = len(self)
            if size:
                self.save(self._savefile, append=self._append)
                self.purge()._append += size
        elif fn is False: self._autoSave = False
        else:
            self._autoSave = size if size else 4096
            self._savefile = fn
            self._append = 0
        return self

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
    def info(f):
        with ZipFile(f) as zf:
            meta = _b2j(zf.read("metadata"))
            meta["len"] = len(zf.namelist()) - 1
            return meta
    
    def _loadMeta(self, zf):
        try: self.meta = _b2j(zf.read("metadata"))
        except: pass

    def _saveMeta(self, zf):
        if self.meta: zf.writestr("metadata", _j2b(self.meta))

    def _load(self, fn, progress=None, start=0, end=None):
        "Load the video from a ZIP file"
        with ZipFile(fn) as zf:
            self._loadMeta(zf)
            self._costumes = []
            i = j = start
            n = len(zf.namelist()) - 1
            while i != end:
                try:
                    data = zf.read(str(i))
                    while not data and i == start and j:
                        j -= 1                        
                        data = zf.read(str(j))
                    if data: data = PixelData(data, True)
                    else: data = self._costumes[i - start - 1]
                    self._costumes.append(data)
                    i += 1
                    if progress: progress(i - start, n)
                except: i = end

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
        vid._costumes = [costumes[i] for i in start]
        vid.meta = dict(self.meta)
        return vid

    def save(self, fn, progress=None, append=False):
        "Save the Video as a zip archive of PixelData binaries"
        self.meta["Saved By"] = "sc8pr{}".format(version)
        fn = fileExt(fn, ["s8v", "zip"])
        with ZipFile(fn, "a" if append else "w") as zf:
            n = len(zf.namelist())
            if n == 0: self._saveMeta(zf)
            if append is True: append = (n - 1) if n else 0
            costumes = self._costumes
            n = len(costumes)
            for i in range(n):
                c = costumes[i]
                if progress: progress(i + 1, n)
                same = i and c == costumes[i - 1]
                fn = str((i + append) if append else i)
                zf.writestr(fn, b'' if same else bytes(c))
        return self

    def capture(self, sk):
        "Capture the current frame of the sketch"
        try: n = self.interval
        except: self.interval = n = 1
        if sk.frameCount % n == 0:
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
        vid = self if inPlace else Video().config(size=size)
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


class Grabber:
    "A class for performing screen captures using PIL.ImageGrab"
    
    def __init__(self, rect=None):
        if rect and not isinstance(rect, pygame.Rect):
            if len(rect) == 2: rect = (0, 0), rect
            rect = pygame.Rect(rect)
        self.rect = rect

    @property
    def bbox(self):
        "Bounding box for capture"
        r = self.rect
        if r: return [r.left, r.top, r.right, r.bottom]

    @property
    def pil(self): return grab(self.bbox)

    @property
    def pix(self): return PixelData(grab(self.bbox))

    @property
    def img(self): return self.pix.img


try:
    import numpy, imageio as im

    class ImageIO:
        "Use imageio and ffmpeg to decode and encode video"

        @staticmethod
        def ffmpeg(p): os.environ["IMAGEIO_FFMPEG_EXE"] = p

        @staticmethod
        def decodev(src, progress=None, vid=None, *args, asList=False):
            "Load a movie file as a Video instance"
            if vid is None: vid = Video()
            with im.get_reader(src) as reader:
                meta = reader.get_meta_data()
                vid.ffmpeg_meta = meta
                i, n = 1, meta.get("nframes")
                vid.size = meta["size"]
                vid.meta["frameRate"] = meta["fps"]
                info = struct.pack("!3I", 0, *vid.size)
                try: # Extra frames/bad metadata in MKV?
                    if len(args) == 0: args = [0]
                    j = 0
                    for f in reader:
                        c, j = ImageIO._crit(i, j, args)
                        if c is None: break
                        elif c: vid += bytes(f), info
                        if progress: progress(i, n)
                        i += 1
                except: pass
            return ImageIO._clipList(vid, *args) if asList else vid

        @staticmethod
        def _crit(i, j, args):
            n = len(args)
            if n % 2 == 0 and i >= args[-1]: c = None
            else:
                if j + 1 < n and i >= args[j+1]: j += 2
                c = i >= args[j]
            return c, j

        @staticmethod
        def _clipList(vid, *args):
            "Separate a discontinuous clip into individual Video instances"
            if not args: return [vid]
            n = len(args) - 1
            args = [args[i+1] - args[i] for i in range(0, n, 2)]
            n = len(vid) - sum(args)
            if n: args.append(n)
            vids = []
            n = 0
            for a in args:
                tmp = vid.clip(n, n+a)
                vids.append(tmp)
                n += a
            return vids

        @staticmethod
        def decodef(src, dest=None, size=512):
            "Convert a video file to s8v format"
            if dest is None: dest = src + ".s8v"
            ImageIO.decodev(src, vid=Video().autoSave(dest, size)).autoSave()

        @staticmethod
        def frameData(img):
            "Format frame data for imageio export"
            if PIL: return numpy.array(img.pil(PIL))
            img = pygame.surfarray.array3d(img.srf)
            return numpy.swapaxes(img, 0, 1)

        @staticmethod
        def encodev(vid, dest, fps=None, progress=None):
            "Save a movie file from a Video instance"
            if isinstance(vid, Video): vid = vid.scaleFrames()
            i, n = 1, len(vid)
            if fps is None: fps = vid.meta.get("frameRate")
            if fps is None: fps = 30
            with im.get_writer(dest, fps=fps) as writer:
                for img in vid.frames():
                    writer.append_data(ImageIO.frameData(img))
                    if progress:
                        progress(i, n)
                        i += 1

        @staticmethod
        def encodef(fn, dest, fps=None, progress=None):
            "Convert an s8v file to using ffmpeg"
            vid = Video(fn, start=0, end=1)
            if fps is None: fps = vid.meta.get("frameRate")
            if fps is None: fps = 30
            i = 0
            with im.get_writer(dest, fps=fps) as writer:
                for img in Video._iter(fn):
                    writer.append_data(ImageIO.frameData(img))
                    if progress:
                        progress(i)
                        i += 1

except: ImageIO = None
