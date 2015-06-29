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

"""Other Shared Code of possibly Dubious Quality.

This module contains code that is/was used in more than one of our projects and
was moved here in order to avoid duplicate code. The intent was:
- not let code diverge (good or bad - better to fix it in one place)
- leverage tests and bug fixes from one repo in other repos

Why "dubious quality"?!

This module may contain code, patterns (anti-patterns) that may not withstand
scrutiny for style, design, etc... The ONLY goal of this module is to avoid
duplicating code. Code here may get cleaned up and graduated into simpl proper
or, if its not good, deleted once we have had the chance to replace or
decommission it from other repos.
"""
