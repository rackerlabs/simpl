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
#
"""Thread-local context utilities.

Usage:

    import threadlocal

    context = threadlocal.default()
    context['value'] = 'foo'

    # somewhere in another module (must be same thread!)
    assert context['value'] == 'foo''

    # create multiple dicts in the same thread
    # with different namespaces
    alt_context = threadlocal.new('custom-namespace')
    alt_context['value'] = 'bar'

    # put an existing dict into your threadlocal context
    context = {'one': 'two', 'buckle': 'shoe'}
    ok = threadlocal.ThreadLocalDict('another-namespace', **context)
    assert ok['buckle'] == 'shoe'

    # threads cannot access each others' ThreadLocalDicts !
    import threading

    threadlocal.default()['foo'] == 'value!'
    def foo_is_none(tld):
        assert threadlocal.default().get('foo') is None

    # the new thread *will not* show a value for 'foo' !
    t = threading.Thread(target=foo_is_none, args=(threadlocal.default(),))
    t.start()
    t.join()
"""

import collections
import threading

THREAD_STORE = threading.local()
DEFAULT_NAMESPACE = 'call_context'


class ThreadLocalDict(collections.MutableMapping):

    """A dict whose data is local to the thread."""

    def __init__(self, namespace, *args, **kwargs):
        """Add namespace to dict constructor."""
        self.namespace = namespace
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        """Show thread-local dict in repr."""
        under = repr(self._get_local_dict())
        return '<%s %s>' % (type(self).__name__, under)

    def _get_local_dict(self):
        """Retrieve (or initialize) the thread-local data to use."""
        try:
            return getattr(THREAD_STORE, self.namespace)
        except AttributeError:
            local_var = dict(*self.args, **self.kwargs)
            setattr(THREAD_STORE, self.namespace, local_var)
            return local_var

    def __len__(self):
        """Return the length of the thread-local dict."""
        return len(self._get_local_dict())

    def __iter__(self):
        """Return an iterator on the thread-local dict."""
        return iter(self._get_local_dict())

    def __getitem__(self, key):
        """Get item on the thread-local dict."""
        return self._get_local_dict()[key]

    def __setitem__(self, key, value):
        """Set item on the thread-local dict."""
        self._get_local_dict()[key] = value

    def __delitem__(self, key):
        """Delete item from the thread-local dict."""
        self._get_local_dict().__delitem__(key)


CONTEXT = ThreadLocalDict(DEFAULT_NAMESPACE)


def default():
    """Get thread-local call context."""
    return CONTEXT


def new(namespace):
    """Get a namespaced ThreadLocalDict."""
    return ThreadLocalDict(namespace)
