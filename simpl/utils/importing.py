"""Utilities for importing.

The function import_me_maybe() uses the signature
of the importlib.import_module() function.

Usage:

    from simpl.utils import import_me_maybe

    eventlet = import_me_maybe('eventlet')
    # this issues a warning (only once) if
    # eventlet is not found

    # to prevent warnings from ever occurring
    from simpl.utils import disable_warnings_for

    # this disables the corresponding warnings globally
    disable_warnings_for('eventlet')

    # this could be in another module

    eventlet = import_me_maybe('eventlet')
    # produces no warning now
"""
import importlib
import inspect
import os
import warnings

from simpl.exceptions import DependencyRequiredWarning


def import_me_maybe(name, package=None):
    """Try to import a module by name and return it.

    If the module is not found, this function returns None.

    Emits a DependencyRequiredWarning if the import fails along
    with information about the caller that needed it.
    Upon success, the specified module will be inserted into
    sys.modules and returned.

    The name argument specifies what module to import in absolute
    or relative terms (e.g. either pkg.mod or ..mod). If the name
    is specified in relative terms, then the package argument must
    be specified to the package which is to act as the anchor for
    resolving the package name
    (e.g. import_module('..mod', 'pkg.subpkg') will import pkg.mod).
    """
    # lookup caller
    importer = inspect.stack()[1]
    importer_frame = importer[0]
    importer_module_name = inspect.getmodulename(importer[1])
    # so this behaves decently in an interpreter
    if importer_module_name:
        if hasattr(inspect, 'getabsfile'):
            importer_path = inspect.getabsfile(importer_frame)
        else:
            importer_path = os.path.abspath(inspect.getfile(importer_frame))
    else:
        importer_path = importer[1]
    fq_path = importer_path.split(os.path.sep)
    if 'simpl' in fq_path:
        # find the rightmost instance of 'simpl' in path
        begin = (len(fq_path) - 1) - fq_path[::-1].index('simpl')
        import_string = '.'.join(fq_path[begin:-1] + [importer_module_name])
    else:
        import_string = importer_module_name or importer[1]
    try:
        mod = importlib.import_module(name, package=package)
    except ImportError as err:
        mod = None
        imp_err = '%s: %s' % (type(err).__name__, str(err))
        warn_msg = DependencyRequiredWarning.format_msg(
            import_string=import_string, requirement=name, from_exc=imp_err)
        warnings.warn(warn_msg, DependencyRequiredWarning, stacklevel=2)
    # it would be fun to inject the dependency here!
    # importer_globals = importer_frame.f_globals
    # importer_globals[name] = mod
    return mod


def disable_warnings_for(name):
    """Disable DependencyRequiredWarning for this requirement."""
    return DependencyRequiredWarning.filter(requirement=name)
