""" Module implementing the FileCopy task.
"""

import errno
import os
import shutil

from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.task_exceptions import TaskValidationException

class FileCopy(Task):
    """ FileCopy Task implementation
    """

    source = TaskAttribute(default_value="", configurable=True, attribute_type=str)
    destination = TaskAttribute(default_value="", configurable=True, attribute_type=str)

    def __init__(self, **kwargs):
        """ Initialize the FileCopy Object

            Args:
                source (str): Source file for FileCopy Task
                destination (str): Destination file for FileCopy Task
        """
        super(FileCopy, self).__init__(**kwargs)

    def validate(self):
        """ Preforms Validation checks for FileCopy Task. Will ensure the source and destination files have been specified, and that the source
            file exists.

            Raises:
                TaskValidationException: FileCopy task is not properly initialized
        """

        if self.source == "" or self.source is None:
            raise TaskValidationException("FileCopy task has no source")

        if self.destination == "" or self.destination is None:
            raise TaskValidationException("FileCopy task has no destination")

        if not os.path.exists(self.source):
            raise TaskValidationException("FileCopy task source file does not exist")

    def setup(self):
        """ Will create destination directory if it does not already exist.

            Raises: 
                OSError: Unable to create destination directory
        """

        if self.destination.endswith(os.sep) or os.path.isdir(self.destination):
            directory = self.destination
        else:
            directory = os.path.dirname(self.destination)

        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise


    def run(self):
        """ Performs file copy.
        """

        shutil.copy2(self.source, self.destination)
        return True