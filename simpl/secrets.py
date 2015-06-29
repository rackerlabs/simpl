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

"""Utilities for managing secrets and sensitive data.

Buyer beware: this module does not make your code secure.
"""

from six.moves.urllib import parse


def hide_url_password(url):
    """Replace a password part of a URL with *****.

    This can be used to scrub URLs before logging them.
    """
    try:
        parsed = parse.urlsplit(url)
        if parsed.password:
            return url.replace(':%s@' % parsed.password, ':*****@')
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:  # pylint: disable=W0703
        pass
    return url
