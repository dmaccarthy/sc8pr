from setuptools import setup, find_packages

version = 2, 2, "a0"
ver = "{}.{}.{}".format(*version)
archive = "master" if version[-1] == "dev" else "v" + ver
with open("README.txt", encoding="utf8") as f: readme = f.read()

setup(
    # Package info
    name = "sc8pr",
    version = ver,
    license = "GPLv3",
    packages = find_packages(),
    package_data = {"sc8pr": ["*.data", "examples/img/*.*"]},

    # Author
    author = "David MacCarthy",
    author_email = "sc8pr.py@gmail.com",

    # Dependencies
    python_requires = ">=3.4, <4",
    install_requires = ["pygame>=1.9.2,<2"],
    
    # URLs
    url = "https://dmaccarthy.github.io/sc8pr",
    download_url = "https://github.com/dmaccarthy/sc8pr/archive/{}.zip".format(archive),

    # Details
    description = "A simple framework for new and experienced Python programmers to create animations, games, robotics simulations, and other graphics-based programs",
    long_description = readme,

    # Additional data
    keywords = "graphics animation sprite gui robotics pygame educational",
    classifiers = [
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: pygame",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Education",
        "Topic :: Games/Entertainment"
    ]
)
