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

    :keyword time_gmt: this is a time_struct, datetime class, or None. If None,
        the current time is used. Its name, time_gmt, is for legacy support for
        functions that called it before it supported multiple values.

    Changing this function will change all times that projects using simpl
        return in their APIs.
    """
    if isinstance(time_gmt, datetime.datetime):
        time_gmt = time_gmt.timetuple()
    if time_gmt is None:
        time_gmt = time.gmtime()
    if isinstance(time_gmt, time.struct_time):
        return time.strftime(API_FORMAT, time_gmt)
    raise TypeError("time_gmt must be a time_struct, datetime, or None. A %s "
                    "was passed." % type(time_gmt))


def parse_time_string(time_string):
    """Convert date/time in API_FORMAT to a datetime."""
    return datetime.datetime.strptime(time_string, API_FORMAT)
