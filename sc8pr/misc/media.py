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

"""
Additional features for encoding and decoding media using additional packages
    (imageio, imageio-ffmpeg, Pillow, numpy)
"""


import os, struct, pygame, numpy, imageio, PIL.Image, PIL.ImageGrab
from sc8pr import PixelData, Image


class Grabber:
    "A class for performing screen captures using PIL.ImageGrab.grab"

    def __init__(self, rect=None):
        self.grab = PIL.ImageGrab.grab
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

    def __init__(self, src, **kwargs):
        self._io = imageio.get_reader(src, **kwargs)
        self._iter = iter(self._io)
        self._meta = self._io.get_meta_data()
        size = kwargs.get("size")
        if size is None: size = self._meta["size"]
        self._info = struct.pack("!3I", 0, *size)

    @property
    def meta(self): return self._meta
    
    def __next__(self):
        "Return the next frame as an uncompressed PixelData instance"
        return PixelData((bytes(next(self._iter)), self._info))

    def __iter__(self):
        "Iterate through all frames returning data as uncompressed PixelData"
        try:
            while True: yield next(self)
        except StopIteration: pass

    def _read(self, n=None, compress=False):
        try:
            while n is None or n > 0:
                pix = next(self)
                if compress: pix.compress()
                if n is not None: n -= 1
                yield pix
        except StopIteration: pass

    def read(self, n=None, alpha=False):
        "Return a list of Images from the next n frames"
        return [img.rgba if alpha else img.img for img in self._read(n)]

    def skip(self, n):
        "Read and discard n frames"
        while n:
            try:
                next(self._iter)
                n -= 1
            except: n = 0
        return self

    def estimateFrames(self):
        "Try to estimate frames from movie metadata"
        try:
            meta = self._meta
            n = meta["nframes"]
            if n == float("inf"):
                n = round(meta["fps"] * meta["duration"])
        except: n = None
        return n


class FFWriter(_FF):
    "Write graphics directly to media file using imageio/FFmpeg"

    def __init__(self, fn, fps=30, **kwargs):
        self._size = None
        self._io = imageio.get_writer(fn, fps=fps, **kwargs)

    def write(self, srf):
        "Write one frame (surface) to the video file, resizing if necessary"
        if type(srf) is not pygame.Surface:
            try: srf = srf.image
            except: srf = Image(srf).image
        size = srf.get_size()
        if self._size is None: self._size = size
        if size != self._size:
            srf = Image(srf).config(size=self._size).image
        self._io.append_data(numpy.array(PixelData(srf).pil))
        return self

    def writePixelData(self, pix):
        "Write a PixelData instance: DOES NOT VERIFY SIZE"
        self._io.append_data(numpy.array(pix.pil))
        return self

    def writePIL(self, pil):
        "Write a PIL image: DOES NOT VERIFY SIZE"
        self._io.append_data(numpy.array(pil))
        return self

    capture = write
