#!/usr/bin/env python
# coding: utf8
import os
from setuptools import setup, find_packages


# Figure out the version.
import re
here = os.path.dirname(os.path.abspath(__file__))
version_re = re.compile(
    r'__version__ = (\(.*?\))')
fp = open(os.path.join(here, 'src/android', '__init__.py'))
version = None
for line in fp:
    match = version_re.search(line)
    if match:
        version = eval(match.group(1))
        break
else:
    raise Exception("Cannot find version in __init__.py")
fp.close()


setup(
    name = 'py-androidbuild',
    version = ".".join(map(str, version)),
    description = 'Routines to build Android projects using Python.',
    long_description = 'Makes it easy to build Android projects in Python, '
                       'or using Python-based build tools.',
    author = 'Michael Elsdörfer',
    author_email = 'michael@elsdoerfer.com',
    license = 'BSD',
    url = 'http://github.com/miracle2k/py-androidbuild/',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Build Tools',
        ],
    entry_points = """[console_scripts]\npy-androidbuild = android.script:run\n""",
    packages = find_packages('src'),
    package_dir = {'': 'src'},
)