# sc8pr

An educational programming package for [Python 3.4+](https://www.python.org). Inspired by [Scratch](https://scratch.mit.edu) and [Processing](https://www.processing.org), sc8pr’s aim is to make it easy for new and experienced Python programmers to create animations, games, and other graphics-based programs.

sc8pr 2 features include:
* a simple, event-driven approach to creating interactive animations
* sprite management
* physics-based collisions
* video effects / transitions
* a selection of GUI controls
* curve plotting
* robotics simulator

For more information, please see the [documentation](http://dmaccarthy.github.io/sc8pr/).

# Installation

Latest release (2.2a2):
```
pip3 install sc8pr==2.2a2
```

Bug fixes for v2.1:
```
pip3 install https://github.com/dmaccarthy/sc8pr/archive/BugFix-2.1.zip
```

Development version (2.2.dev):
```
pip3 install https://github.com/dmaccarthy/sc8pr/archive/master.zip
```

Please note that as of 2021 October 6, **pygame 1.9** is available on PyPI.org up to Python 3.8 only. Attempting to install an older version of **sc8pr** in Python 3.9 may fail as the **pygame** requirement is unavailable. For Python 3.9, you can use **sc8pr** versions (2.1.3+, 2.2.a2+) compatible with **pygame 2.0**.

See the documentation for more [detailed instructions](https://dmaccarthy.github.io/sc8pr/?inst).

# Try It First

**sc8pr** is pure Python 3 code, so you can try it without running the setup. Just unzip the **sc8pr** package into your PYTHONPATH. You will still need **pygame** installed.
