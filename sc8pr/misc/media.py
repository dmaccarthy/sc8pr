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


import os, struct, pygame
from sc8pr import PixelData
from sc8pr.misc.video import Video


class Grabber:
    "A class for performing screen captures using PIL.ImageGrab.grab"
    
    def __init__(self, grab, rect=None):
        self.grab = grab
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


class ImageIO:
    "Use imageio and ffmpeg to decode and encode video"
    
    @staticmethod
    def init(im, ff=None):
        ImageIO.im = im
        if ff: os.environ["IMAGEIO_FFMPEG_EXE"] = ff

    @staticmethod
    def ffmpeg(p): os.environ["IMAGEIO_FFMPEG_EXE"] = p

    @staticmethod
    def decodev(src, progress=None, vid=None, *args, asList=False):
        "Load a movie file as a Video instance"
        if vid is None: vid = Video()
        with ImageIO.im.get_reader(src) as reader:
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
    def frameData(img, np, PIL=None):
        "Format frame data for imageio export"
        if PIL: return np.array(img.pil(PIL))
        img = pygame.surfarray.array3d(img.srf)
        return np.swapaxes(img, 0, 1)

    @staticmethod
    def encodev(vid, dest, fps=None, progress=None):
        "Save a movie file from a Video instance"
        if isinstance(vid, Video): vid = vid.scaleFrames()
        i, n = 1, len(vid)
        if fps is None: fps = vid.meta.get("frameRate")
        if fps is None: fps = 30
        with ImageIO.im.get_writer(dest, fps=fps) as writer:
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
        with ImageIO.im.get_writer(dest, fps=fps) as writer:
            for img in Video._iter(fn):
                writer.append_data(ImageIO.frameData(img))
                if progress:
                    progress(i)
                    i += 1
