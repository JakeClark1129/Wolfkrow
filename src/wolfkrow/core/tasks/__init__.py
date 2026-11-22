# Magic dictionary which is automatically populated with ALL wolfkrow.core.tasks.task.Task objects defined. 
# (They only need to be imported -- See Below)
all_tasks = {}

# Import all the wolfkrow.core.tasks.task.Task objects we can find.
# Note: Will always search this current directory plus all directories found in 
# the 'WOLFKROW_TASK_SEARCH_PATHS' environment variable.

from os.path import dirname, basename, isfile, join
import glob
modules = glob.glob(join(dirname(__file__), "*.py"))
ignored_modules = ["__init__.py"]
__all__ = [ basename(f)[:-3] for f in modules if isfile(f) and basename(f) not in ignored_modules]

# Search current directory first.
from . import *

# Search direcotries found in the WOLFKROW_TASK_SEARCH_PATHS.
# Note: Tasks defined more than once will overwrite and previous definitions found.

import os
PATH_SEP = os.path.pathsep

import importlib.util
import sys


def _load_source(module_name, file_path):
    """ Replacement for the deprecated `imp.load_source` (Removed in Python 3.12) """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


search_paths = os.environ.get('WOLFKROW_TASK_SEARCH_PATHS')
if search_paths:
    for item in search_paths.split(PATH_SEP):
        if os.path.isdir(item):
            files = os.listdir(item)
            for file_name in files:
                if file_name.endswith(".py"):
                    basename = file_name[:-3]
                    module_name = "wolfkrow.core.tasks.{task_module}".format(
                        task_module=basename
                    )
                    file_path = os.path.join(item, file_name)
                    _load_source(module_name, file_path)


def describe_all_tasks(include_abstract=False):
    """ Returns a JSON serializable description of every registered Task type.

    Used by external tools (Such as the Wolfkrow Editor) to build nodes for each
    Task type without needing to know anything about the Task implementations.

    Kwargs:
        include_abstract (bool): Whether to include base Task types which are 
            not intended to be used directly in a config. (Any Task type 
            which sets `abstract = True` on its class)
    """
    descriptions = {}
    for task_name, task_class in sorted(all_tasks.items()):
        if not include_abstract and task_class.__dict__.get("abstract", False):
            continue
        descriptions[task_name] = task_class.describe()
    return descriptions
