from distutils.core import setup

with open("README.txt") as f: readme = f.read()

setup(name="sc8pr", version="1.0.0", license = "GPLv3", requires = ["pygame(>=1.9.1)"],
    packages = ["sc8pr"],
    package_data = {"": ["icons/*.*", "robot/*.*", "*.json"]},

    # Author
    author = "David MacCarthy",
    author_email = "devwigs@gmail.com",

    # Details
    url = "http://dmaccarthy.github.io/sc8pr",
    download_url = "https://github.com/dmaccarthy/sc8pr/archive/v1.0.0.zip",
    description = "Create interactive animations with features inspired by Scratch, Processing, and robotics",
    long_description = readme
)
