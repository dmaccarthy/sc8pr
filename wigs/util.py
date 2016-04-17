# Copyright 2015-2016 D.G. MacCarthy <devwigs@gmail.com>
#
# This file is part of WIGS.
#
# WIGS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# WIGS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with WIGS.  If not, see <http://www.gnu.org/licenses/>.


from traceback import format_exc
from sys import stderr
from zipfile import ZipFile as zf, ZIP_DEFLATED
from random import randint
import pygame, wigs, os
from pygame.color import Color


ARROW = pygame.cursors.arrow
DIAMOND = pygame.cursors.diamond
MOVE = ((16,16),(9,8),(1,128,3,192,7,224,1,128,1,128,17,136,49,140,127,254,127,254,49,140,17,136,1,128,1,128,7,224,3,192,1,128),(3,192,7,224,15,240,7,224,3,192,59,220,127,254,255,255,255,255,127,254,59,220,3,192,7,224,15,240,7,224,3,192))
TEXT = ((16,16),(4,7),(119,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,119,0),(119,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,8,0,119,0))
CROSS = ((16,16),(8,8),(1,0,1,0,1,0,1,0,1,0,0,0,0,0,248,62,0,0,0,0,1,0,1,0,1,0,1,0,1,0,0,0),(1,0,1,0,1,0,1,0,1,0,0,0,0,0,248,62,0,0,0,0,1,0,1,0,1,0,1,0,1,0,0,0))
HAND = ((16,24),(6,1),(6,0,9,0,9,0,9,0,9,192,9,56,9,38,105,37,153,37,136,37,64,1,32,1,16,1,8,1,8,1,4,1,4,2,3,252,0,0,0,0,0,0,0,0,0,0,0,0),(6,0,15,0,15,0,15,0,15,192,15,184,15,254,111,253,255,253,255,255,127,255,63,255,31,255,15,255,15,255,7,255,7,254,3,252,0,0,0,0,0,0,0,0,0,0,0,0))
MENU = ((16,16),(3,2),(0,0,127,254,127,254,0,0,0,0,0,0,127,254,127,254,0,0,0,0,0,0,127,254,127,254,0,0,0,0,0,0),(255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,0,0,0,0))
NO_CURSOR = ((8,8),(5,4),(0,0,0,0,0,0,0,0),(0,0,0,0,0,0,0,0))

def setCursor(c):
    if not c: c = ARROW
    pygame.mouse.set_cursor(*c)

def nothing(*args): pass
def logError(): print(format_exc(), file=stderr)

def randPixel(obj):
    w, h = obj.size
    return randint(0, w-1), randint(0, h-1)

def rgba(*args):
    c = [Color(*c) if type(c) is tuple else Color(c) for c in args]
    return c[0] if len(c) == 1 else c

#def rgb(h): return Color(h<<8 | 255)
#def rgbList(*args): return [rgb(c) for c in args]

def randColor(alpha=False):
    return Color(*[randint(0,255) for i in range(4 if alpha else 3)])

def getAlpha(c):
    if type(c) in (tuple, list):
        return c[3] if len(c) == 4 else 255
    return c.a

def keyMod(): return pygame.key.get_mods() & 963 != 0
def altKey(): return pygame.key.get_mods() & 768 != 0
def controlKey(): return pygame.key.get_mods() & 192 != 0
def shiftKey(): return pygame.key.get_mods() & 3 != 0

def dragging(ev, button=None):
    if ev.type == pygame.MOUSEMOTION:
        return (max(ev.buttons) if button is None else ev.buttons[button-1]) > 0
    return False

def isChar(u): return ord(u) >= 32 if len(u) else False
def isEnter(k): return k.key in (10, 13)
def isHome(k): return k.key == pygame.K_HOME or k.key == pygame.K_KP7 and k.unicode == ""
def isEnd(k): return k.key == pygame.K_END or k.key == pygame.K_KP1 and k.unicode == ""
def isPgUp(k): return k.key == pygame.K_PAGEUP or k.key == pygame.K_KP9 and k.unicode == ""
def isPgDn(k): return k.key == pygame.K_PAGEDOWN or k.key == pygame.K_KP3 and k.unicode == ""
def isLeft(k): return k.key == pygame.K_LEFT or k.key == pygame.K_KP4 and k.unicode == ""
def isRight(k): return k.key == pygame.K_RIGHT or k.key == pygame.K_KP6 and k.unicode == ""
def isUp(k): return k.key == pygame.K_UP or k.key == pygame.K_KP8 and k.unicode == ""
def isDown(k): return k.key == pygame.K_DOWN or k.key == pygame.K_KP2 and k.unicode == ""
def isIncr(k): return k.key in (pygame.K_UP, pygame.K_RIGHT) or k.key in (pygame.K_KP8, pygame.K_KP6) and k.unicode == ""
def isDecr(k): return k.key in (pygame.K_DOWN, pygame.K_LEFT) or k.key in (pygame.K_KP2, pygame.K_KP4) and k.unicode == ""

def copyAttr(src, dest):
    if type(src) != dict: src = src.__dict__
    for k in src: setattr(dest, k, src[k])

def getValues(*args, **kwargs):
    return tuple([kwargs.get(k) for k in args])

def eventKey(ev, eMap):
    "Determine eventMap key: (1) ev.type, (2) type(ev), (3) None"
    if ev.type in eMap: key = ev.type
    elif type(ev) in eMap: key = type(ev)
    else: key = None
    return key

def handleEvent(obj, ev):
    "Call an event handler from an object's eventMap attribute"
    eMap = obj.eventMap
    key = eventKey(ev, eMap)
    return eMap[key](obj, ev) if key in eMap else None

def fontHeight(f):
    if not isinstance(f, pygame.font.Font): f = f.font
    return f.get_linesize() + 1

def saveZip(zName, fName, data=None):
    z = zf(zName, "a", ZIP_DEFLATED)
    z.writestr(fName, data)
    z.close()
    return z

# def array(n, val=0):
#     "Create a list of n items initialized to the given value"
#     return [val for i in range(n)]

def containsAny(obj, items='*?|<>"'):
    for i in items:
        if i in obj: return True
    return False

def wigsPath(rel=""):
    "Return path to wigs folder"
    path = wigs.__path__[0]
    if rel: path += "/" + rel
    return os.path.normpath(path)


# Numerical integration...

def _step(dt, *derivs):
    n = 0
    f = dt
    for d in derivs:
        n += 1
        if n == 1: val = list(d)
        else:
            val = [val[i] + d[i] * f for i in range(len(d))]
            f *= dt / n
    return tuple(val)

def step(dt, *args):
    return [_step(dt, *args[i:]) for i in range(len(args)-1)]


# Classes...

class StaticClassException(Exception):
    def __init__(self, cls): super().__init__("{} is static; constructor should not be called".format(cls))


class Data:
    "Object-oriented dict-like data structure"
    def get(self, key): return self.__dict__.get(key)
    def attr(self, **kwargs): self.__dict__.update(**kwargs)
    def keys(self): return self.__dict__.keys()
    def empty(self): self.__dict__.clear()
    __init__ = attr
    
    def __str__(self):
        t = type(self)
        return "<{}.{} {}>".format(t.__module__, t.__name__, self.__dict__)
    