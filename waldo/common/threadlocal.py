"""Threadlocal."""
import threading

THREAD_STORE = threading.local()


class LocalDict(object):

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

    def __getitem__(self, key):
        return self._get_local_dict()[key]

    def __setitem__(self, key, value):
        self._get_local_dict()[key] = value

    def __delitem__(self, key):
        self._get_local_dict().__delitem__(key)

    def __contains__(self, key):
        self._get_local_dict().__contains__(key)

    def get(self, key, *args):
        """Implement dict.get()."""
        return self._get_local_dict().get(key, *args)

    def update(self, *args, **kwargs):
        """Implement dict.update()."""
        return self._get_local_dict().update(*args, **kwargs)

    def setdefault(self, key, value):
        """Implement dict.setdefault()."""
        return self._get_local_dict().setdefault(key, value)


CONTEXT = LocalDict('call_context')


def get_context():
    """Get thread-local call context."""
    return CONTEXT
