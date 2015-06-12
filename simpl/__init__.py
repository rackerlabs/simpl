# Copyright 2015 Rackspace US, Inc.
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
"""simpl common utlities library."""
__title__ = 'simpl'
__version__ = '0.1.1'
__license__ = 'Apache 2.0'
__copyright__ = 'Copyright Rackspace US, Inc. (c) 2015'
__url__ = 'https://github.com/checkmate/simpl'

import os

from simpl import config  # flake8: noqa
from simpl import git  # flake8: noqa
from simpl.exceptions import *


IS_TRAVIS_CI_ENV = all(map(os.environ.get, ['TRAVIS', 'CI']))
