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


class Cache:
    
    def __init__(self, maxSize=1):
        self._cacheMax = maxSize
        self._cache = []
        self._cacheKeys = []

#    def __len__(self): return len(self._cache)

    def keys(self):
        for k in self._cacheKeys: yield k

    def index(self, key):
        try:
            return self._cacheKeys.index(key)
        except:
            return None 
    
    def get(self, key):
        i = self.index(key)
        return None if i is None else self._cache[i]

    def put(self, key, val):
        i = self.index(key)
        if i is None:
            self._cache.append(val)
            self._cacheKeys.append(key)
            if len(self._cache) > self._cacheMax:
                self._cache = self._cache[1:]
                self._cacheKeys = self._cacheKeys[1:]
        else: self._cache[i] = val
