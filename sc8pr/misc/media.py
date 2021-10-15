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

"""
Additional features for encoding and decoding media using additional packages
    (imageio, imageio-ffmpeg, Pillow, numpy)
"""


import os, struct, pygame
from sc8pr import PixelData, Graphic, Image, version
from sc8pr.misc.video import Video
from sc8pr.misc.s8v import S8Vfile
from sys import modules


class Grabber:
    "A class for performing screen captures using PIL.ImageGrab.grab"

    def __init__(self, rect=None):
        self.grab = modules["PIL.ImageGrab"].grab
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
    def pil(self): return self.grab(self.bbox)

    @property
    def pix(self): return PixelData(self.grab(self.bbox))

    @property
    def img(self): return self.pix.img


class _FF:

    @staticmethod
    def ffmpeg(ff): os.environ["IMAGEIO_FFMPEG_EXE"] = ff

    def __enter__(self): return self
    def __exit__(self, *args): self._io.close()
    close = __exit__


class FFReader(_FF):
    "Read images directly from a media file using imageio/FFmpeg"

    def __init__(self, fn):
        self._io = r = modules["imageio"].get_reader(fn)
        self._iter = iter(self._io)
        self.meta = r.get_meta_data()
        self._info = struct.pack("!3I", 0, *self.meta["size"])

    def __next__(self):
        "Return the next frame as an uncompressed PixelData instance"
        return PixelData((next(self._iter), self._info))

    def read(self, n=None):
        "Return a Video instance from the next n frames"
        vid = Video()
        while n or n is None:
            try: vid += next(self._iter), self._info
            except: n = 0
            if n: n -= 1
        return vid

    def skip(self, n):
        "Read and discard n frames"
        while n:
            try:
                next(self._iter)
                n -= 1
            except: n = 0
        return self

    def __iter__(self):
        "Iterate through all frames returning data as uncompressed PixelData"
        for f in self._io:
            yield PixelData((bytes(f), self._info))

    def estimateFrames(self):
        "Try to estimate frames from movie metadata"
        try:
            meta = self.meta
            n = meta["nframes"]
            if n == float("inf"):
                n = round(meta["fps"] * meta["duration"])
        except: n = None
        return n

    @staticmethod
    def convert(fn, progress=None):
        "Read a movie and write it as an S8V file"
        with FFReader(fn) as src:
            fn += ".s8v"
            with S8Vfile(fn, "x", fps=src.meta["fps"]) as s8v:
                n = 0
                f = src.estimateFrames()
                for frame in src:
                    s8v.append(bytes(PixelData(frame, True)))
                    n += 1
                    if progress: progress(n, f)
        return fn


class FFWriter(_FF):
    "Write graphics directly to media file using imageio/FFmpeg"

    @staticmethod
    def _createFrameData():
        pil = modules.get("PIL.Image")
        np = modules["numpy"]
        if pil: return lambda img: np.array(img.pil)
        else: return lambda img: np.swapaxes(pygame.surfarray.array3d(img.srf), 0, 1)

    def __init__(self, fn, fps=30):
        self._fd = FFWriter._createFrameData()
        self._size = None
        self._io = modules["imageio"].get_writer(fn, fps=fps)

    def write(self, img):
        "Write one frame to the video file"
        try: srf = img.image
        except: srf = Image(img).image
        size = srf.get_size()
        if self._size is None: self._size = size
        if size != self._size:
            srf = Image(srf).config(size=self._size).image
        data = self._fd(PixelData(srf))
        self._io.append_data(data)
        return self

    @staticmethod
    def encode(vid, dest=None, fps=None):
        "Encode a Video instance or S8V file using FFmpeg"
        isVid = isinstance(vid, Video)
        if isVid and fps is None: fps = vid.meta.get("frameRate")
        if fps is None: fps = 30
        if dest is None:
            dest = "movie.mp4" if isVid else vid + ".mp4"
        with FFWriter(dest, fps) as ffw:
            if isVid:
                for f in vid.scaleFrames().frames():
                    ffw._io.append_data(ffw._fd(f))
            else:
                with S8Vfile(vid) as s8v:
                    size = None
                    for f in s8v.clip():
                        if size is None: size = f.size
                        if f.size != size:
                            f = PixelData(f.img.config(size=size), True)
                        ffw._io.append_data(ffw._fd(f))
