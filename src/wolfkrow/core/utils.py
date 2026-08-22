from builtins import object

import os
import sys
import yaml

from importlib import reload
from types import ModuleType




def wolfkrow_reload(module):
    """ Recursively reload all wolfkrow modules. Intended to be used in development, 
    when making changes and you don't want to restart the interpreter. (Typically
    when testing in a DCC like Nuke.)

    NOTE: Only recurses into submodules of the module passed in. Will not reload
        any other dependencies that the module may have.
    """
    reload(module)
    modules = list(sys.modules.values())
    for module_ in modules:
        if module_ is None:
            continue
        if module_.__name__ == module.__name__:
            continue
        if not isinstance(module_, ModuleType):
            continue
        if module_.__name__.startswith(module.__name__ + "."):
            # This shouldn't really be recursive, but without the recursion call, 
            # we end up reloading the task module after loading all the individual 
            # tasks. This means that the task module sets the all_tasks dictionary 
            # to an empty dictionary, and removes all the tasks that were loaded 
            # (Tasks add them selves to this dictionary as they are imported).
            # Recursive here doesn't "solve" this problem, but it does just happen
            # to load things in the correct order, so lets just leave it for now.
            wolfkrow_reload(module_)
