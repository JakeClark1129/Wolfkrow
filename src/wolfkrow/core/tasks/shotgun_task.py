""" Module implementing the FileCopy task.
"""

import errno
import os
import shutil
import subprocess

from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.task_exceptions import TaskValidationException

class ShotgunTask(Task):
    """ Base Task for all tasks that interact with shotgun. This task handles 
        creation of a shotgun connection, and authentication.
    """

    shotgun_site = TaskAttribute(
        default_value=None, 
        required=True ,
        configurable=False,
        description="The url to your shotgun site."
    )

    authenticated_user = TaskAttribute(
        default_value=None,
        required=False,
        configurable=False,
        description="Serialized authenticated user to be deserialized on the farm.")

    script_name = TaskAttribute(
        default_value=None,
        required=False,
        configurable=False,
        description="The name of the script as it is registered in shotgun."
    )

    api_key = TaskAttribute(
        default_value=None,
        required=False,
        configurable=False,
        description="The unique identifier of the API key for the script being run."
    )

    def __init__(self, **kwargs):
        """ Initialize the ShotgunTask Object

            Args:
        """
        super(ShotgunTask, self).__init__(**kwargs)

    def validate(self):
        """ Preforms Validation checks to ensure the ShotgunTask Task is properly initialized.

            Raises:
                TaskValidationException: ShotgunTask task is not properly initialized
        """

        for attr_name, attr in list(self.task_attributes.items()):
            if attr.required is True and getattr(self, attr_name) is None:
                
                raise TaskValidationException("Required argument {arg} not supplied.".format(
                    arg=attr_name
                ))

    def setup(self):
        """ Sets up shotgun connection to be used later in the run method.
        """
        if self.authenticated_user is not None:
            # in some cases, the '\n' character will be interpreted as '\\n' (backslash, 
            # and an n). Fix that here.
            self.authenticated_user = self.authenticated_user.replace("\\n", "\n")

            import sgtk
            user = sgtk.authentication.deserialize_user(self.authenticated_user)
            self._sg = user.create_sg_connection()
        else:
            import shotgun_api3
            self._sg = shotgun_api3.Shotgun(
                self.shotgun_site, 
                script_name=self.script_name, 
                api_key=self.api_key
            )