

##### Task Graph #####
# Import objects from the task_graph module
from wolfkrow.config.scene import WolfkrowScene

from .core.engine.task_graph import TaskGraph
from .core.engine.task_graph import TaskGraphValidationException, TaskGraphException

##### Tasks #####
# Import the tasks so that they are available at the top level
from .core import tasks
all_tasks = tasks.all_tasks

##### Loader #####
from .config.workflow_builder import Loader
from .config.workflow_builder import LoaderException

##### Utils #####
from .core.utils import wolfkrow_reload

def load_scene(wolfkrow_scene_file):
    """ Loads a wolfkrow scene file and returns a WolfkrowScene object.
    """
    return WolfkrowScene(wolfkrow_scene_file)