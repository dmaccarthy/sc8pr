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


class ImageIO:
    "Use imageio and ffmpeg to decode and encode video"

    @staticmethod
    def ffmpeg(ff): os.environ["IMAGEIO_FFMPEG_EXE"] = ff

    @staticmethod
    def decode(src, *args, save=None, purge=False, progress=None):
        "Load a movie file as a list of Video clips"
        if not args: args = (0,),
        vid = [Video() for a in args]
        with modules["imageio"].get_reader(src) as reader:
            meta = reader.get_meta_data()
            i, n = 0, meta.get("nframes")
            for clip in vid:
                clip.ffmpeg_meta = meta
                clip.size = meta["size"]
                clip.meta["frameRate"] = meta["fps"]
            clip = 0
            info = struct.pack("!3I", 0, *vid[0].size)
            a = args[0]
            try: # Extra frames/bad metadata in MKV?
                for f in reader:
                    if len(a) == 2 and a[1] == i:
                        if save: vid[clip].save(save.format(clip))
                        if purge: vid[clip].purge()
                        clip += 1
                        if clip >= len(args): break
                        a = args[clip]
                    if i >= a[0]: vid[clip] += bytes(f), info
                    if progress: progress(i)
                    i += 1
            except: pass
        return vid if args and len(args) > 1 else vid[0]

    @staticmethod
    def _createFrameData():
        pil = modules.get("PIL.Image")
        np = modules["numpy"]
        if pil: return lambda img: np.array(img.pil)
        else: return lambda img: np.swapaxes(pygame.surfarray.array3d(img.srf), 0, 1)

    @staticmethod
    def encode(vid, save="movie.mp4", progress=None):
        "Encode a movie from a Video instance or s8v file"
        if type(vid) is str: vid = Video(vid)
        fps = vid.meta.get("frameRate")
        vid = vid.scaleFrames()
        i, n = 1, len(vid)
        with modules["imageio"].get_writer(save, fps=(fps if fps else 30)) as writer:
            fd = ImageIO._createFrameData()
            for img in vid.frames():
                writer.append_data(fd(img))
                if progress:
                    progress(i, n)
                    i += 1
