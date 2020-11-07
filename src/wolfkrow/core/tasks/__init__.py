# Magic dictionary which is automatically populated with ALL wolfkrow.core.tasks.task.Task objects defined. 
# (They only need to be imported)
all_tasks = {}


from os.path import dirname, basename, isfile, join
import glob
modules = glob.glob(join(dirname(__file__), "*.py"))
ignored_modules = ["__init__.py"]
__all__ = [ basename(f)[:-3] for f in modules if isfile(f) and basename(f) not in ignored_modules]

from . import *