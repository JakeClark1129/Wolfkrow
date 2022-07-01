""" Module implementing a nuke render task.
"""

from .task import Task, TaskAttribute
from .task_exceptions import TaskValidationException
from .nuke_render import NukeTask

class ProcessCutref(NukeTask):
    """ ProcessCutref Task implementation.
    """

    source = TaskAttribute(default_value="", configurable=True, attribute_type=str)
    
    retime_first = TaskAttribute(required=True, configurable=True, attribute_type=int, description="Frame number to retime the first frame to")
    retime_last = TaskAttribute(required=True, configurable=True, attribute_type=int, description="Frame number to retime the last frame to")
    start_frame = TaskAttribute(required=True, configurable=True, attribute_type=int, description="Start processing at this frame")
    end_frame = TaskAttribute(required=True, configurable=True, attribute_type=int, description="End processing at this frame")
    frame_rate = TaskAttribute(default_value=24.0, configurable=True, attribute_type=float, description="Frame rate to render at")
    render_path = TaskAttribute(required=True, configurable=True, attribute_type=str)
    publish_id = TaskAttribute(required=False, configurable=True, attribute_type=int, description="Shotgun ID of the entity in shotgun to update the status of after render is complete.")

    def __init__(self, **kwargs):
        """ Initialize the ProcessCutref Object

            Kwargs:
        """
        super(ProcessCutref, self).__init__(**kwargs)
        self.executable = "wolfkrow_nuke"

    def validate(self):
        """ Preforms Validation checks for ProcessCutref Task.

            Raises:
                TaskValidationException: ProcessCutref task is not properly initialized
        """
        pass

    def setup(self):
        """ Will create destination directory if it does not already exist.

            Raises: 
                OSError: Unable to create destination directory
        """
        pass

    def run(self):
        """ Performs the nuke render.
        """

        from shotgun_utils import publish_utils
        from cutref_utils import cutref_utils

        result = cutref_utils.retime_and_cut_clip(
            self.source,
            self.retime_first,
            self.retime_last,
            self.start_frame,
            self.end_frame,
            self.frame_rate,
            self.render_path
        )

        if result:
            exit_code = 0
            publish_status = "cmpt"

        else:
            exit_code = 1
            publish_status = "error"

        if self.publish_id:
            publish_utils.update_status("PublishedFile", self.publish_id, publish_status)

        return exit_code