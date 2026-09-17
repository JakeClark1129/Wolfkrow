""" Module implementing the FileCopy task.
"""

import re

from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.task_exceptions import TaskValidationException


class ShotgunTask(Task):
    """ Base Task for all tasks that interact with shotgun. This task handles 
        creation of a shotgun connection, and authentication.
    """

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
        pass
