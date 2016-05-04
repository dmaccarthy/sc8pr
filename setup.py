from distutils.core import setup

setup(name="scropr", version="0.7a", packages = ["scropr"],

    # Author
    author = "David MacCarthy",
    author_email = "devwigs@gmail.com",

    # Details
    url = "http://pypi.python.org/pypi/?/",
    license = "LICENSE",
    description = "Interactive animation programming",
    long_description = open("README.md").read(),
    include_package_data = True,

    # Dependencies
    install_requires = ["pygame"]
)