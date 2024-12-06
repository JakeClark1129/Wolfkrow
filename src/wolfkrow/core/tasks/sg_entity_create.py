""" Module implementing the FileCopy task.
"""

import errno
import os
import shutil
import subprocess

from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.shotgun_task import ShotgunTask
from wolfkrow.core.tasks.task_exceptions import TaskValidationException

class ShotgunCreateEntity(ShotgunTask):
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

    entity_code = TaskAttribute(
        default_value=None,
        required=False,
        configurable=True,
        attribute_type=str,
        description="The code of the entity to create. If provided, will first "
            "attempt to find the entity by code and update it rather than creating "
             "a new entity. \n\nNOTE: If you always want to create a new entity, "
             "do not provide this attribute, instead pass it in via the fields attribute."
    )

    overwrite = TaskAttribute(
        default_value=False,
        required=False,
        configurable=True,
        attribute_type=bool,
        description="If True, will overwrite the entity if it already exists, otherwise the Task will fail."
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
        super(ShotgunCreateEntity, self).__init__(**kwargs)

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

        # First check if the entity already exists
        entity = self._sg.find_one(self.entity_type, [["code", "is", self.entity_code]])

        if entity:
            if self.overwrite:
                entity = self._sg.update(self.entity_type, entity["id"], fields)
                print("Updated exiting entity: {}".format(entity))
                return 0
            else:
                print("Entity already exists and overwrite is False. Exiting.")
                return 1
        else:
            entity = self._sg.create(self.entity_type, fields)
            print("Created entity: {}".format(entity))


        return 0