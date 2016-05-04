# Copyright 2015-2016 D.G. MacCarthy <http://dmaccarthy.github.io>
#
# This file is part of "scropr".
#
# "scropr" is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "scropr" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "scropr".  If not, see <http://www.gnu.org/licenses/>.


"""Functions for searching sequences of objects based on their attribute values"""

def search(items, match=None, **kwargs):
    "Generator to search a group of objects"
    if match is None: match = match_eq
    for s in items:
        if match(s, **kwargs): yield s

def match_eq(item, matchAny=False, **kwargs):
    "Search for matches based on attribute equality"
    for k in kwargs:
        m = True
        if hasattr(item, k):
            if getattr(item, k) != kwargs[k]:
                m = False
        else:
            m = False
        if m and matchAny or not (m or matchAny):
            return m
    return not matchAny

def match_has(item, matchAny=False, **kwargs):
    "Search for matches based on attribute existence"
    matchAll = not matchAny
    for k in kwargs:
        if hasattr(item, k) == kwargs[k]:
            if matchAny: return True
        elif matchAll: return False
    return matchAll
