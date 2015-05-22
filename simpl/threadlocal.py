"""Threadlocal."""
import collections
import threading

THREAD_STORE = threading.local()


class LocalDict(collections.MutableMapping):

    """A dict whose data is local to the thread."""

    def __init__(self, varname, *args, **kwargs):
        self.varname = varname
        self.args = args
        self.kwargs = kwargs

    def _get_local_dict(self):
        """Retrieve (or initialize) the thread-local data to use."""
        local_var = getattr(THREAD_STORE, self.varname, None)
        if not local_var:
            local_var = dict(*self.args, **self.kwargs)
            setattr(THREAD_STORE, self.varname, local_var)
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


CONTEXT = LocalDict('call_context')


def get_context():
    """Get thread-local call context."""
    return CONTEXT
