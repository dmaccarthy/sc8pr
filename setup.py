from setuptools import setup, find_packages

version = 2, 0, "dev"
ver = "{}.{}.{}".format(*version)
archive = "master" if version[-1] == "dev" else "v" + ver
with open("README.txt") as f: readme = f.read()

setup(
    # Package info
    name = "sc8pr",
    version = ver,
    license = "GPLv3",
    packages = find_packages(),
    package_data = {"sc8pr": ["*.data", "examples/img/*.*"]},

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
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Education"
    ]
)
