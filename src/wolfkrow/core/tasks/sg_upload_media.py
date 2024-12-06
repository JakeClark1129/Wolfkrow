""" Module implementing the FileCopy task.
"""

import errno
import os
import shutil
import subprocess

from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.shotgun_task import ShotgunTask
from wolfkrow.core.tasks.task_exceptions import TaskValidationException

class ShotgunUploadMedia(ShotgunTask):
    """ Shotgun Upload Media Task implementation. Will upload a single quicktime/mp4 file to 
        a shotgun entity.
    """

    source = TaskAttribute(
        default_value=None, 
        required=True, 
        configurable=True, 
        attribute_type=str, 
        description="The file path to a media file to upload to shotgun"
    )

    entity_type = TaskAttribute(
        default_value="Version",
        required=False,
        configurable=True,
        attribute_type=str, 
        description="Type of entity to upload the Quicktime to."
    )

    upload_field = TaskAttribute(
        default_value="sg_uploaded_movie",
        required=False,
        configurable=True,
        attribute_type=str, 
        description="The field on the entity to upload the Quicktime to."
    )

    retry_count = TaskAttribute(
        default_value=5,
        required=False,
        configurable=True,
        attribute_type=int, 
        description="The number of times to retry the upload if it fails."
    )

    shotgun_id = TaskAttribute(
        default_value=None,
        required=True,
        configurable=True,
        attribute_type=int, 
        description="The id of the shotgun entity to upload the Quicktime to."
    )


    def __init__(self, **kwargs):
        """ Initialize the Task Object
        """
        super(ShotgunUploadMedia, self).__init__(**kwargs)

    def run(self):
        """ Preforms the media upload
        """

        for i in range(self.retry_count):
            try:
                self._sg.upload(self.entity_type, self.shotgun_id, self.source, field_name=self.upload_field)
                break
            except Exception as e:
                print("Retry count exceeded. Failed to upload media: {}".format(self.source))
                if i == self.retry_count - 1:
                    raise

        return 0