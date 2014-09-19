import threading


threadlocal = threading.local()

def threadlocal_var(varname, factory, *a, **k):
  v = getattr(threadlocal, varname, None)
  if v is None:
    v = factory(*a, **k)
    setattr(threadlocal, varname, v)
  return v

threadlocaldict = threadlocal_var('threadlocal_context', dict)
