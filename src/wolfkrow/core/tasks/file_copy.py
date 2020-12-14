""" Module implementing the FileCopy task.
"""

import errno
import os
import shutil

from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.task_exceptions import TaskValidationException

class FileCopy(Task):
    """ FileCopy Task implementation.
        
        Note: This task also handles copying sequences of files. To do this, include 
        a "%04d" style string in your source, and destination file paths.
            You can also leave the destination as a directory, but must include 
            a trailing slash OR ensure the directory exists ahead of time.
    """

    source = TaskAttribute(default_value="", attribute_type=str)
    destination = TaskAttribute(default_value="", attribute_type=str)

    # Optional attributes used when when the source files are a sequence.
    start_frame = TaskAttribute(
        default_value=None,
        attribute_type=int, 
        description="Start frame of the source frames to copy."
    )
    end_frame = TaskAttribute(
        default_value=None,
        attribute_type=int, 
        description="End frame of the source frames to copy."
    )
    renumbered_start_frame = TaskAttribute(
        default_value=None,
        attribute_type=int, 
        description="Start frame to renumber the destination sequence to."
    )

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

        # Regex to check if the source and destination files are intended to be sequences or not.
        self.sequence_identifier = "(%.[0-9]+d)"

        import re
        source_filename = os.path.basename(self.source)
        if re.search(self.sequence_identifier, source_filename):
            return self.copy_sequence()

        shutil.copy2(self.source, self.destination)
        return 0

    def copy_sequence(self):
        import re
        # Get the regexp match in order to isolate the part of the path that represents the frame numbers.
        source_dirname, source_filename = os.path.split(self.source)
        match = re.search(self.sequence_identifier, source_filename)
        if not match:
            print("Path {path} does not represent a sequence".format(path=self.source))
            return 1

        # Check if destination path represents a sequence, or is a directory.
        destination_filename = os.path.basename(self.destination)
        dest_is_dir = False
        dest_match = re.search(self.sequence_identifier, destination_filename)
        if not dest_match:
            # Destination is not a sequence. Check if the destination is a directory:
            if self.destination.endswith(os.sep):
                dest_is_dir = True
            elif os.path.isdir(self.destination):
                dest_is_dir = True
            else:
                print("Destination path {path} is not a sequence, or a directory."
                    "If this was not expected, then please ensure the destination "
                    "directory exists or include a trailing '{os_sep}' in the path".format(
                        path=self.destination,
                        os_sep=os.sep
                    )
                )
                return 1

        # Glob the source sequence to get a list of files to copy.
        import glob
        glob_pattern = source_dirname + os.sep + source_filename[0:match.start()] + "*" + source_filename[match.end():]
        files = glob.glob(glob_pattern)
        # Sort so that the frames are in order
        files = sorted(files)

        # There are no files to copy.
        if len(files) == 0:
            return 0

        # Determine the frame offset in order to renumber source frames to destination frames.
        file_basename = os.path.basename(files[0])
        source_start_frame = self.start_frame or int(file_basename[match.start():match.end() - len(source_filename)])
        destination_frame_offset = self.renumbered_start_frame - source_start_frame

        # Copy each frame
        for f in files:
            file_basename = os.path.basename(f)
            frame = int(file_basename[match.start():match.end() - len(source_filename)])

            # Ensure the current frame is within the range of frames to copy.
            if self.start_frame and self.end_frame:
                if frame < self.start_frame or frame > self.end_frame:
                    continue

            # Apply the frame offset
            frame = frame + destination_frame_offset

            if dest_is_dir:
                source_basename = source_filename[0:match.start()] + str(frame) + source_filename[match.end():]
                dest = os.path.join(self.destination, source_basename)
            else:
                dest = self.destination % frame
            shutil.copy2(f, dest)
        return 0