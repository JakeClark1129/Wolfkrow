""" Module implementing the FileCopy task.
"""

import errno
import os
import shutil

from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.file_operation import FileOperation
from wolfkrow.core.tasks.task_exceptions import TaskValidationException

class FileCopy(FileOperation):
    """ FileCopy Task implementation.
        
        Note: This task also handles copying sequences of files. To do this, include 
        a "%04d" style string in your source, and destination file paths.
            You can also leave the destination as a directory, but must include 
            a trailing slash OR ensure the directory exists ahead of time.
    """

    source_permission = TaskAttribute(default_value=None, configurable=True, attribute_type=int)
    destination_permission = TaskAttribute(default_value=None, configurable=True, attribute_type=int)

    def operate(self, source, destination):
        print(f"Copying {source} --> {destination}")
        shutil.copy2(source, destination)

        if self.source_permission:
            print(f"Setting Source File permission: {self.source_permission}")
            self.set_permission(source, self.source_permission)

        if self.destination_permission:
            print(f"Setting Destination File permission: {self.destination_permission}")
            self.set_permission(destination, self.destination_permission)
