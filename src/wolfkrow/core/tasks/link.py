""" Module implementing the FileCopy task.
"""

import errno
import os
import shutil

from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.file_operation import FileOperation
from wolfkrow.core.tasks.task_exceptions import TaskValidationException

class Link(FileOperation):
    """ Link Task implementation (Linux Only). Simple wrapper around the 'ln' command in Linux.

        Note: This task also handles linking sequences of files. To do this, include 
        a "%04d" style string in your source, and destination file paths.
            You can also leave the destination as a directory, but must include 
            a trailing slash OR ensure the directory exists ahead of time.
    """

    link_type = TaskAttribute(default_value="symlink", attribute_options=["symlink", "hardlink"])

    def validate(self):
        """ Preforms Validation checks for the Link Task. Will check to make sure 
            that the source file is not a directory for hardlinking.

            Raises:
                TaskValidationException: FileOperation task is not properly initialized
        """

        super(Link, self).validate()

        # Cannot hard link directories
        if self.link_type == "hardlink":
            if os.path.isdir(self.source):
                raise TaskValidationException("Source {} is a directory.")

            if os.path.isdir(self.destination):
                if os.path.dirname(self.source) == os.path.dirname(self.destination):
                    raise TaskValidationException("Destination {} cannot be the "
                        "same directory as the source directory if no file name "
                        "is specified".format(self.destination))

    def operate(self, source, destination):
        if self.link_type == "symlink":
            os.symlink(source, destination)
        elif self.link_type == "hardlink":
            os.link(source, destination)