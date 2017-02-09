from setuptools import setup
from sc8pr import __version__ as ver, __dev__

archive = "master" if __dev__ else "v{}".format(ver)
with open("README.txt") as f: readme = f.read()

setup(
    # Package info
    name = "sc8pr",
    version = ver,
    license = "GPLv3",
    packages = ["sc8pr"],
    package_data = {"sc8pr": ["*.json", "icons/*.*", "robot/*.*"]},

    # Author
    author = "David MacCarthy",
    author_email = "devwigs@gmail.com",

    # Dependencies
    install_requires = ["pygame(>=1.9.1)"],
    
    # URLs
    url = "http://dmaccarthy.github.io/sc8pr",
    download_url = "https://github.com/dmaccarthy/sc8pr/archive/{}.zip".format(archive),

    # Details
    description = "Create interactive animations with features inspired by Scratch, Processing, and robotics",
    long_description = readme,

    # Additional data
    keywords = "graphics animation sprite gui robotics pygame educational",
    classifiers = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Education"
    ]
)