""" Module implementing the FileCopy task.
"""

import errno
import os
import shutil
import subprocess

from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.shotgun_task import ShotgunTask
from wolfkrow.core.tasks.task_exceptions import TaskValidationException

class ShotgunUploadThumbnail(ShotgunTask):
    """ Shotgun Upload Thumbnail Task implementation. Will upload a thumbnail to 
        a shotgun entity.
    """

    source = TaskAttribute(
        default_value=None, 
        required=True, 
        configurable=True, 
        attribute_type=str, 
        description="The file path to an image to upload to shotgun as a thumbnail"
    )

    entity_type = TaskAttribute(
        default_value=None,
        required=True,
        configurable=True,
        attribute_type=str, 
        description="Type of entity to upload the thumbnail to. Required by the upload_thumbnail method in shotgun."
    )

    shotgun_id = TaskAttribute(
        default_value=None,
        required=True,
        configurable=True,
        attribute_type=int, 
        description="The id of the shotgun entity to upload the thumbnail to. Required by the upload_thumbnail method in shotgun."
    )


    def __init__(self, **kwargs):
        """ Initialize the Rawline Object

            Args:
        """
        super(ShotgunUploadThumbnail, self).__init__(**kwargs)

    def validate(self):
        """ Preforms Validation checks to ensure the Rawline Task is properly initialized.

            Raises:
                TaskValidationException: Rawline task is not properly initialized
        """

        for attr_name, attr in list(self.task_attributes.items()):
            if attr.required is True and getattr(self, attr_name) is None:
                
                raise TaskValidationException("Required argument {arg} not supplied.".format(
                    arg=attr_name
                ))

    def run(self):
        """ Preforms the thumbnail upload
        """

        self._sg.upload_thumbnail(self.entity_type, self.shotgun_id, self.source)
        return 0