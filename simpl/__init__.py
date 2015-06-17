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

"""Simpl."""

import os

from simpl import config  # noqa
from simpl import git  # noqa
from simpl.exceptions import *  # noqa
from simpl.__about__ import *  # noqa


IS_TRAVIS_CI_ENV = all(map(os.environ.get, ['TRAVIS', 'CI']))
