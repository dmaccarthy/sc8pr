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


import os, struct, zlib, pygame
from zipfile import ZipFile
from json import loads, dumps
from sc8pr import Image, version
from sc8pr.sprite import Sprite
from sc8pr.util import hasAlpha
try: from PIL import Image as PImage
except: PImage = None


def jsonToBytes(obj):
    return bytes(dumps(obj, ensure_ascii=False), encoding="utf-8")

def jsonFromBytes(b):
    return loads(str(b, encoding="utf-8"))

def _saveRaw(img, fn, frmt=0):
    "Save image as raw bytes"
    data = convert(img, frmt)
    with open(fn, "wb") as f:
        for b in data: f.write(b)

def convert(img, frmt=1):
    """Convert between pygame.Surface, PIL.Image, and binary data;
    only RGB and RGBA modes are supported"""
    # 0 = Uncompressed bytes
    # 1 = Compressed bytes
    # 2 = pygame.Surface
    # 3 = PIL.Image
    if type(img) is tuple:
        data = img[0]
        mode, w, h = struct.unpack("!3I", img[1])
        if mode & 2: data = zlib.decompress(data)
        mode = ["RGB", "RGBA"][mode & 1]
        size = w, h
        if frmt == 2: return pygame.image.fromstring(data, size, mode)
        if frmt == 3: return PImage.frombytes(mode, size, data)
        _formatError()
    try: isPIL = isinstance(img, PImage.Image)
    except: isPIL = False
    if isPIL:
        _formatError(frmt, 0, 1, 2)
        data = img.tobytes()
        if frmt == 2: return pygame.image.fromstring(data, img.size, img.mode)
        return _image_bin(data, img.mode, img.size, frmt)
    if not isinstance(img, pygame.Surface): img = img.image
    _formatError(frmt, 0, 1, 3)
    size = img.get_size()
    mode = "RGBA" if hasAlpha(img) else "RGB"
    data = pygame.image.tostring(img, mode)
    if frmt == 3: return PImage.frombytes(mode, size, data)
    return _image_bin(data, mode, size, frmt)

def _image_bin(data, mode, size, compress=1):
    "Return a 2-tuple of binary (data, (mode,size))"
    mode = ["RGB", "RGBA"].index(mode)
    if compress:
        mode += 2
        data = zlib.compress(data)
    mode = struct.pack("!3I", mode, *size)
    return data, mode

def _formatError(n=None, *args):
    if n not in args: raise ValueError("Invalid format")


class Video(Sprite):
    "A class for storing and retrieving sequences of compressed images"
    _current = None,

    def __init__(self, data=None, alpha=False, progress=None):
        self.alpha = alpha
        self.meta = {}
        self._costumes = []
        t = type(data)
        if t is str: self._load(data, progress)
        elif t is tuple and type(data[0]) is int: self._size = data
        elif data:
            self._costumes = [convert(img) for img in data]
        if len(self._costumes):
            img = Image(*self._costumes[0])
            self._size = img.size
            self._current = 0, img

    def __len__(self): return len(self._costumes)

    def __iadd__(self, img):
        "Append a frame to the video"
        self._costumes.append(convert(img))
        if not hasattr(self, "_size"): self._size = img.size
        return self

    def __getitem__(self, n):
        "Return a frame as an Image instance"
        if n != self._current[0]:
            self._current = n, Image(*self._costumes[n])
        img = self._current[1]
        srf = img.original
        if self.alpha and not hasAlpha(srf):
            img = Image(srf.convert_alpha())
            self._current = n, img
        return img.config(size=self.size, angle=self.angle)

    def costume(self):
        "Return the current costume"
        return self[self.costumeNumber]

    def extend(self, imgs):
        "Append multiple frames to the video"
        self._costumes.extend(convert(img) for img in imgs)
        return self

    def _loadMeta(self, zf):
        try: self.meta = jsonFromBytes(zf.read("metadata"))
        except: pass

    def _saveMeta(self, zf):
        if self.meta: zf.writestr("metadata", jsonToBytes(self.meta))

    def _load(self, fn, progress=None):
        "Load the video from a ZIP file"
        with ZipFile(fn) as zf:
            self._loadMeta(zf)
            self._costumes = []
            i = 0
            while i >= 0:
                try:
                    data = zf.read(str(i))
                    if data: data = data[:-12], data[-12:]
                    else: data = self._costumes[i-1]
                    self._costumes.append(data)
                    i += 1
                    if progress: progress(i, None, False)
                except:
                    i = -1
                    if progress: progress(None, None, False)

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

    def save(self, fn, progress=None):
        "Save the Video as a zip archive of zlib-compressed images"
        self.meta["Saved By"] = "sc8pr{}".format(version)
        with ZipFile(fn, "w") as zf:
            self._saveMeta(zf)
            costumes = self._costumes
            n = len(costumes)
            for i in range(n):
                if progress: progress(i + 1, n, True)
                data, mode = costumes[i]
                zf.writestr(str(i), b'' if i and costumes[i] == costumes[i-1] else data + mode)
        return self

    def capture(self, sk):
        "Capture the current frame of the sketch"
        try: n = self.interval
        except: self.interval = n = 1
        if sk.frameCount % n == 0: self += sk

    def scaleFrames(self, size=None, inPlace=False):
        "Ensure all frame images have the same size"
        if not size: size = self.size
        vid = self if inPlace else Video().config(size=size)
        for i in range(len(self)):
            img, mode = self._costumes[i]
            mode, w, h = struct.unpack("!3I", mode)
            if (w, h) != size:
                img = self[i].config(size=size).snapshot()
                if inPlace: self._costumes[i] = convert(img)
                else: vid += img
            elif not inPlace: vid._costumes.append(self._costumes[i])
        return vid


try:
    import imageio as im
    import numpy

    class ImageIO:
        "Use imageio and ffmpeg to decode and encode video"

        @staticmethod
        def ffmpeg(p): os.environ["IMAGEIO_FFMPEG_EXE"] = p

        @staticmethod
        def decode(src, progress=None):
            "Load a movie file as a Video instance"
            vid = Video()
            with im.get_reader(src) as reader:
                meta = reader.get_meta_data()
                i, n = 1, meta.get("nframes")
                vid.size = meta["size"]
                vid.meta["frameRate"] = meta["fps"]
                try: # Extra frames/bad metadata in MKV?
                    for f in reader:
                        vid._costumes.append((zlib.compress(bytes(f)),
                            struct.pack("!3I", 2, *vid.size)))
                        if progress:
                            progress(i, n, False)
                            i += 1
                except: pass
            return vid

        @staticmethod
        def pilFrame(img):
            "Format frame image data using PIL"
            if not isinstance(img, PImage.Image):
                img = convert(img, 3)
            return numpy.array(img)

        @staticmethod
        def srfFrame(img):
            "Format frame image data using pygame.surfarray"
            if isinstance(img, Image): img = img.image
            if not isinstance(img, pygame.Surface):
                img = convert(img, 2)
            img = pygame.surfarray.array3d(img)
            return numpy.swapaxes(img, 0, 1)

        @staticmethod
        def encode(vid, dest, fps=None, progress=None):
            "Save Video or image sequence as a movie"
            if isinstance(vid, Video): vid = vid.scaleFrames()
            i, n = 1, len(vid)
            if fps is None: fps = vid.meta.get("frameRate")
            if fps is None: fps = 30
            if isinstance(vid, Video): vid = vid._costumes
            frame = ImageIO.pilFrame if PImage else ImageIO.srfFrame
            with im.get_writer(dest, fps=fps) as writer:
                for img in vid:
                    writer.append_data(frame(img))
                    if progress:
                        progress(i, n, True)
                        i += 1

except: ImageIO = None
