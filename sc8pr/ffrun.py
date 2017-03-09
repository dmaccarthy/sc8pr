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


"Run FFmpeg as a subprocess"


from os.path import exists
import subprocess as sp

if hasattr(sp, "run"):
# Python 3.5+: Use subprocess.run
	def run(args): return sp.run(args, stdout=sp.PIPE, stderr=sp.PIPE)

else:
# Python 3.4-: Use subprocess.call

    from tempfile import TemporaryFile

    class CompletedProcess:

        def __init__(self, args, code, out, err):
            self.returncode = code
            self.stdout = out
            self.stderr = err
            self.args =args

        def __str__(self):
            s = "{}(args={}, returncode={}, stdout={}, stderr={})"
            return s.format(type(self).__name__, self.args,
                self.returncode, self.stdout, self.stderr)


    def run(args):
        with TemporaryFile("w+b") as out:
            with TemporaryFile("w+b") as err:
                code = sp.call(args, stdout=out, stderr=err)
                out.seek(0)
                outb = out.read()
                err.seek(0)
                errb = err.read()
        return CompletedProcess(args, code, outb, errb)


class FF:
    "Static class for encoding using FFmpeg"

    AUDIO = 1
    VIDEO = 2
    cmd = "ffmpeg"

    @staticmethod
    def _exists(fn, n=1):
        "Raise an exception if the destination file exists"
        fn = fn.format(n)
        if exists(fn): raise FileExistsError(fn)

    @staticmethod
    def run(args): return run([FF.cmd] + args)

    @staticmethod
    def convert(src, dest, av=3):
        "Convert media to another format using container defaults"
        FF._exists(dest)
        codec = [["-vn"], ["-an"], []][av - 1]
        return FF.run(["-i", src] + codec + [dest])

    @staticmethod
    def encode(src, dest, fps=30, **kwargs):
        "Encode a sequence of images as a video stream"
        fps = str(fps)
        n = kwargs.get("start")
        FF._exists(dest, n if n is not None else 1)
        cmd = ["-f", "image2", "-r", fps]
        if n: cmd.extend(["-start_number", str(n)])
        cmd.extend(["-i", src, "-r", fps])
        for key in ("vcodec", "pix_fmt", "vframes"): cmd.extend(FF._opt(kwargs, key))
        cmd.append(dest)
        return FF.run(cmd)

    @staticmethod
    def _opt(options, key):
        "Get an FFmpeg option from the dictionary"
        val = options.get(key)
        return ["-" + key, str(val)] if val else []
