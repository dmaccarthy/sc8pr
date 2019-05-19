# Copyright 2015-2019 D.G. MacCarthy <http://dmaccarthy.github.io>
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


import pygame

class EventManager:
    "A class for inspecting and dispatching events"

    def __init__(self, sk):
        self.sk = sk
        self.focus = sk
        self.hover = sk
        self.drag = None

    def dispatch(self, ev):
        # Record mouse and keyboard events
        sk = self.sk
        other = False
        key = hasattr(ev, "key")
        if key: sk.key = ev
        elif hasattr(ev, "pos"): sk.mouse = ev
        else: other = True

        # Trigger sk.onevent
        if hasattr(sk, "onevent"):
            if sk.onevent(ev): return

        # Get event target and handler name
        path = sk.objectAt(sk.mouse.pos).path
        if not path: path = [sk]
        setattr(ev, "target", path[0])
        name = "on" + pygame.event.event_name(ev.type).lower()

        # Send events other than mouse or keyboard to the sketch handler
        if other:
            name = name.replace("event", "")
            self.handle(sk, name, ev)

        # Send KEYDOWN and KEYUP events to the focused object
        elif key:
            current = self.focus
            if current is None: current = sk
            setattr(ev, "target", current)
            self.handle(current.path, name, ev)

        # Send MOUSEDOWN events to the onblur, onfocus and onclick
        # methods of the respective objects, while setting focus
        elif ev.type == pygame.MOUSEBUTTONDOWN:
            for p in path:
                if p.focusable:
                    focus = p
                    break
            if self.drag is not None: self._dragRelease(ev)
            if self.focus is not focus: # elif in 2.1!
                if hasattr(self.focus, "onblur"):
                    setattr(ev, "target", self.focus)
                    getattr(self.focus, "onblur")(ev)
                    setattr(ev, "target", path[0])
                self.focus = focus
                self.handle(path, "onfocus", ev)
            self.handle(path, "onclick", ev)

        # Send MOUSEUP events to the object bring dragged
        elif ev.type == pygame.MOUSEBUTTONUP:
            if not self._dragRelease(ev):
                self.handle(path, "onmouseup", ev)

        # Send MOUSEMOTION events to the onmouseout and onmouseover
        # methods of the respective objects; trigger ondrag method
        # if an object is begin dragged
        elif ev.type == pygame.MOUSEMOTION:
            self._overOut(path, ev)
            drag = False
            if sum(ev.buttons): # Dragging
                if self.drag is not None: hoverPath = self.drag.path
                else: hoverPath = self.hover.path
                current = _find(hoverPath, "ondrag")
                if current is not None:
                    if self.drag is not current:
                        self.drag = current
                    getattr(current, "ondrag")(ev)
                    drag = True
            if not drag: self.handle(path, "onmousemotion", ev)

        # Trigger sk.onhandled
        self.hover = path[0]
        if hasattr(sk, "onhandled"):
            delattr(ev, "target")
            sk.onhandled(ev)

    def handle(self, path, eventName, ev):
        "Locate and call the appropriate event handler"
        if type(path) is not list: path = path.path
        current = _find(path, eventName)
        if current is None: current = path[0]
        if hasattr(current, eventName):
            return getattr(current, eventName)(ev)

    def _dragRelease(self, ev):
        drag = self.drag
        if drag:
            if hasattr(drag, "onrelease"):
                getattr(drag, "onrelease")(ev)
            drag = True
        else: drag = False
        self.drag = None
        return drag

    def _overOut(self, path, ev):
        oldHover = self.hover.path
        obj = oldHover[0]
        while obj not in path:
            setattr(ev, "target", obj)
            self.handle(obj, "onmouseout", ev)
            obj = obj.canvas
        i = path.index(obj)
        for obj in reversed(path[:i]):
            setattr(ev, "target", obj)
            self.handle(obj, "onmouseover", ev)


def _find(p, a):
    "Find an object in the path that has the given attribute"
    for i in range(len(p)):
        g = p[i]
        if hasattr(g, a): return g
