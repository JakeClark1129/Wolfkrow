""" Module implementing the FileCopy task.
"""

import errno
import os
import shutil
import subprocess

from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.shotgun_task import ShotgunTask
from wolfkrow.core.tasks.task_exceptions import TaskValidationException

class ShotgunUpdateEntity(ShotgunTask):
    """ Shotgun Upload Thumbnail Task implementation. Will upload a thumbnail to 
        a shotgun entity.
    """

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

    fields = TaskAttribute(
        default_value=None,
        required=True,
        configurable=True,
        attribute_type=dict,
        description="A dictionary of fields to update on the entity."
    )

    def __init__(self, **kwargs):
        """ Initialize the Rawline Object

            Args:
        """
        super(ShotgunUpdateEntity, self).__init__(**kwargs)

    def validate(self):
        """ Preforms Validation checks to ensure the Rawline Task is properly initialized.

            Raises:
                TaskValidationException: Rawline task is not properly initialized
        """

        # TODO: Why is this here and not in the parent Task definition?
        for attr_name, attr in list(self.task_attributes.items()):
            if attr.required is True and getattr(self, attr_name) is None:
                
                raise TaskValidationException("Required argument {arg} not supplied.".format(
                    arg=attr_name
                ))

    def run(self):
        """ Preforms the thumbnail upload
        """

        fields = self.process_sg_fields(self.fields)

        entity = self._sg.update(self.entity_type, self.shotgun_id, fields)
        print("Updated entity: {}".format(entity))
        print("Fields: {}".format(self.fields))

        return 0