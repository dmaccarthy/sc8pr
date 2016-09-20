# Copyright 2015-2016 D.G. MacCarthy <http://dmaccarthy.github.io>
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

from os.path import isdir
from os import mkdir
from json import dump
from sc8pr.util import logError
from sys import stderr
from threading import Thread


class _SaveThread(Thread):
    
    def __init__(self, ramFolder):
        super().__init__()
        self.rf = ramFolder

    def run(self):
        print("Saving RAMFolder...", file=stderr)
        self.rf.save()
        print("Done!", file=stderr)


class RAMFolder:
    "A class for storing data in memory for delayed writing to disk"
    
    def __init__(self, name, parent=None):
        "Create a folder in RAM"
        self.data = {}
        self.parent = parent
        self.name = name

    def items(self): return self.data.items()

    def __iter__(self):
        for i in self.data: yield i

    def __getitem__(self, k): return self.data[k]

    def __setitem__(self, key, obj):
        """Add an item to the folder or subfolder...
            key = Eventual file name
            obj = Data as object; if mutable, value when SAVED (not when added!) will be written"""
        key = key.replace("\\", "/").split("/")
        path = [k.replace(":", "") for k in key[:-1]]
        name = key[-1]
        fldr = self
        for k in path:
            if k not in ("", ".", ".."):
                if k in fldr:
                    if not isinstance(fldr[k], RAMFolder):
                        raise TypeError("Cannot add item to non-folder")
                else:
                    fldr.data[k] = RAMFolder(k, fldr)
                fldr = fldr.data[k]
        fldr.data[name] = obj

    def traverse(self, recursive=True):
        "Iterate through items in the folder and subfolders"
        for k, v  in self.items():
            if isinstance(v, RAMFolder):
                yield v.path, v
                if recursive:
                    for j in v.traverse():
                        yield j
            else:
                yield self.path + k, v

    def ls(self, recursive=True):
        "Print a listing of the folder contents to the console"
        for k, v in self.traverse(recursive):
            print("{} [{}]".format(k, type(v).__name__))
    
    @property
    def pathList(self):
        "Return a list of ancestor folders"
        f = self
        p = []
        while f.parent:
            p.append(f)
            f = f.parent
        p.append(f)
        return p

    @property
    def path(self):
        "Return the folder's location relative to the root folder as a string"
        s = ""
        for f in reversed(self.pathList):
            s += f.name + "/"
        return s

    def save(self, removeAfterSave=True, recursive=True):
        "Save the contents of a folder and its subfolders"
        remove = []
        count = 0
        for k, v in self.items():
            try:
                if isinstance(v, RAMFolder): # Save sub-folder
                    if recursive:
                        if not isdir(v.path): mkdir(v.path)
                        v.save(removeAfterSave, recursive)
                else:
                    fn = self.path + k
                    t = type(v)
                    if t in (set, frozenset):
                        v = sorted(v)
                        t = list
                    if hasattr(v, "saveAs"): # Save object using its saveAs method
                        v.saveAs(fn)
                    elif t in (bytes, bytearray): # Save binary data
                        with open(fn, "wb") as output: output.write(v)
                    elif v is None or t in (str, tuple, list, dict, bool, int, float):
                        # Save other data as text or JSON with UTF-8 encoding
                        with open(fn, "w", encoding="utf8") as output:
                            if t is str: output.write(v)
                            else: dump(v, output, ensure_ascii=False)
                    else: # Unknown data type
                        raise TypeError("Unable to save instance of {}".format(t))
                    if removeAfterSave: remove.append(k) 
                    count += 1
                    if count % 25 == 0: print("Saved {} items in {}".format(count, self.path), file=stderr)
            except: logError()
        for k in remove: del self.data[k]

    def saveInNewThread(self): _SaveThread(self).start()
