"""Threadlocal."""
import threading


THREADLOCAL = threading.local()


def threadlocal_var(varname, factory, *a, **k):
    """Return or set a threadlocal attribute."""
    val = getattr(THREADLOCAL, varname, None)
    if val is None:
        val = factory(*a, **k)
        setattr(THREADLOCAL, varname, val)
    return val


THREADLOCALDICT = threadlocal_var('threadlocal_context', dict)
