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

"""simpl packaging, installation, and package attributes."""

import os
from setuptools import find_packages
from setuptools import setup


src_dir = os.path.dirname(os.path.realpath(__file__))

about = {}
with open(os.path.join(src_dir, 'simpl', '__about__.py')) as abt:
    exec(abt.read(), about)


INSTALL_REQUIRES = [
    'six',
]

TESTS_REQUIRE = [
    'mock',
]

CLASSIFIERS = [
    'Intended Audience :: Developers',
    'License :: OSI Approved :: Apache Software License',
    'Operating System :: OS Independent',
    'Topic :: Software Development',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.4',
]

package_attributes = {
    'name': about['__title__'],
    'description': about['__summary__'],
    'keywords': ' '.join(about['__keywords__']),
    'version': about['__version__'],
    'tests_require': TESTS_REQUIRE,
    'test_suite': 'tests',
    'install_requires': INSTALL_REQUIRES,
    'packages': find_packages(exclude=['tests']),
    'author': about['__author__'],
    'maintainer_email': about['__email__'],
    'classifiers': CLASSIFIERS,
    'license': about['__license__'],
    'url': about['__url__'],
}


setup(**package_attributes)
