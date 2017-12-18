# sc8pr

An educational programming package for [Python 3.4+](https://www.python.org). Inspired by [Scratch](https://scratch.mit.edu) and [Processing](https://www.processing.org), sc8pr’s aim is to make it easy for new and experienced Python programmers to create animations, games, and other graphics-based programs.

sc8pr 2.0 features include:
* a simple, event-driven approach to creating interactive animations
* sprite management
* physics-based collisions
* video effects / transitions
* a selection of GUI controls
* curve plotting
* robotics simulator

For more information, please see the [documentation](http://dmaccarthy.github.io/sc8pr/).

# Installation

Ensure that you have Python 3.4 or higher installed. Run the following commands as an administrator.

Windows...
```
py -3 -m pip install setuptools
py -3 -m pip install https://github.com/dmaccarthy/sc8pr/archive/master.zip
```

Most other systems...
```
sudo pip3 install setuptools
sudo pip3 install https://github.com/dmaccarthy/sc8pr/archive/master.zip
```

If setuptools is unable to locate a Pygame wheel for your platform and Python version, you will need to install [pygame](http://www.pygame.org) separately.

# Try It First

sc8pr is pure Python 3 code, so you can try it without running the setup. Just unzip the sc8pr package into your PYTHONPATH. You will still need pygame installed.
