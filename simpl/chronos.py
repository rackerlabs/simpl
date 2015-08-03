# Copyright (c) 2011-2015 Rackspace US, Inc.
# All Rights Reserved.
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Simpl time utilities.

Use for consistent date/time conversion and date/time formatting in APIs.

In code, get current time formatted as a string using
`chronos.get_time_string()`. Date/times are always UTC. We leave it to clients
to convert to local time.

Our APIs consitently return date/time in the API_FORMAT format.
"""

import datetime
import time

API_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def get_time_string(time_gmt=None):
    """The canonical time string format (in UTC).

    Changing this function will change all times that this project uses in
    the API returned data.
    """
    assert time_gmt is None or isinstance(time_gmt, time.struct_time), (
        "time_gmt must be a time_struct or none, not a %s" % type(time_gmt))
    return time.strftime(API_FORMAT, time_gmt or time.gmtime())


def parse_time_string(time_string):
    """Convert date/time in API_FORMAT to a datetime."""
    return datetime.datetime.strptime(time_string, API_FORMAT)
