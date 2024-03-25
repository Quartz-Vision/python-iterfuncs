import pathlib

import setuptools

ROOT = pathlib.Path(__file__).parent.resolve()

with open(ROOT / "README.md", "r") as fh:
    long_description = fh.read()

with open(ROOT / "requirements.txt") as fr:
    reqs = fr.read().strip().split("\n")


setuptools.setup(
    name="iterfuncs",
    version="0.1.2",
    author="liava",
    author_email="liava@tuta.io",
    description="Collection of iteration, caching and async tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Quartz-Vision/python-iterfuncs",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
    install_requires=reqs,
    package_data={
        "iterfuncs": [],
    },
    entry_points={
        # "console_scripts": ["sometool=.cli:cli"],
    },
)
