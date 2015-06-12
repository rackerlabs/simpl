#!/usr/bin/env python

# Copyright 2013-2015 Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""simpl packaging and installation."""

import ast
import re
from setuptools import find_packages
from setuptools import setup


DEPENDENCIES = [
    'six',
]
TESTS_REQUIRE = [
    'mock',
]


def package_meta():
    """Read __init__.py for global package metadata.

    Do this without importing the package.
    """
    _version_re = re.compile(r'__version__\s+=\s+(.*)')
    _url_re = re.compile(r'__url__\s+=\s+(.*)')
    _license_re = re.compile(r'__license__\s+=\s+(.*)')

    with open('simpl/__init__.py', 'rb') as simplinit:
        initcontent = simplinit.read()
        version = str(ast.literal_eval(_version_re.search(
            initcontent.decode('utf-8')).group(1)))
        url = str(ast.literal_eval(_url_re.search(
            initcontent.decode('utf-8')).group(1)))
        licencia = str(ast.literal_eval(_license_re.search(
            initcontent.decode('utf-8')).group(1)))
    return {
        'version': version,
        'license': licencia,
        'url': url,
    }

_simpl_meta = package_meta()


setup(
    name='simpl',
    description='Python common libraries',
    keywords='common reusable amazing',
    version=_simpl_meta['version'],
    tests_require=TESTS_REQUIRE,
    test_suite='tests',
    install_requires=DEPENDENCIES,
    packages=find_packages(exclude=['tests']),
    maintainer='Sam Stavinoha',
    maintainer_email='samuel.stavinoha@rackspace.com',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Topic :: Software Development',
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
    ],
    license=_simpl_meta['license'],
    url=_simpl_meta['url'],
)
