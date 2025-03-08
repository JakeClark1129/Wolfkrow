""" Module implementing the FileCopy task.
"""

import errno
import os
import shutil

from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.file_operation import FileOperation
from wolfkrow.core.tasks.task_exceptions import TaskValidationException

class FileMove(FileOperation):
    """ FileCopy Task implementation.
        
        Note: This task also handles copying sequences of files. To do this, include 
        a "%04d" style string in your source, and destination file paths.
            You can also leave the destination as a directory, but must include 
            a trailing slash OR ensure the directory exists ahead of time.
    """

    def __init__(self, **kwargs):
        """ Override the chunkable attribute to False for file moves.
        """
        super(FileOperation, self).__init__(**kwargs)
        # File moves are so quick that doing them in chunks makes them take longer.
        self.chunkable = False

    def operate(self, source, destination):
        shutil.move(source, destination)
