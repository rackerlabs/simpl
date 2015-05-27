"""Threadlocal."""
import collections
import threading

THREAD_STORE = threading.local()
DEFAULT_NAMESPACE = 'call_context'


class ThreadLocalDict(collections.MutableMapping):

    """A dict whose data is local to the thread."""

    def __init__(self, namespace, *args, **kwargs):
        self.namespace = namespace
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):

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
        return len(self._get_local_dict())

    def __iter__(self):
        return iter(self._get_local_dict())

    def __getitem__(self, key):
        return self._get_local_dict()[key]

    def __setitem__(self, key, value):
        self._get_local_dict()[key] = value

    def __delitem__(self, key):
        self._get_local_dict().__delitem__(key)


CONTEXT = ThreadLocalDict(DEFAULT_NAMESPACE)


def get_context():
    """Get thread-local call context."""
    return CONTEXT
