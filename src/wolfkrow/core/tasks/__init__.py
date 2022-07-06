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

# Search current direcotry first.
from . import *

# Search direcotries found in the WOLFKROW_TASK_SEARCH_PATHS.
# Note: Tasks defined more than once will overwrite and previous definitions found.

PATH_SEP = ":"

import imp
import os
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
                    imp.load_source(module_name, file_path)