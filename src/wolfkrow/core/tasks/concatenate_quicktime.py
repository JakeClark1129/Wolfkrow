""" Module implementing the ConcatenateQuicktime task.
"""
from __future__ import print_function

from builtins import str
import errno
import glob
import os
import subprocess

from wolfkrow.core.tasks.task import Task, TaskAttribute

class ConcatenateQuicktime(Task):
    """ ConcatenateQuicktime Task implementation
    """

    ffmpeg_executable = TaskAttribute(
        default_value=None,
        configurable=True,
        attribute_type=str,
        description=("The path to the ffmpeg executable. Defaults to ffmpeg and "
            "assumes that it's added to PATH. If this is not the case, then you "
            "must modify this attribute to point to the full ffmpeg path on your machine.")
    )

    source = TaskAttribute(
        default_value=None, 
        configurable=True, 
        attribute_type=str,
        required=True,
        description="The Path to the mov's to concatenate. Use a wildcard to specify multiple files. (e.g. /path/to/movs/*.mov)"
    )

    destination = TaskAttribute(
        default_value=None, 
        configurable=True, 
        attribute_type=str, 
        description="The path to the final mov file to write out."
    )

    def __init__(self, **kwargs):
        super(ConcatenateQuicktime, self).__init__(**kwargs)

        if self.ffmpeg_executable is None:
            self.ffmpeg_executable = os.environ.get("WOLFKROW_DEFAULT_FFMPEG_EXECUTABLE", "ffmpeg")

    def setup(self):
        """ Ensures that the destination directory exists, and creates the ffmpeg
        input text file which contains all the input quicktimes found.
        """
        destination_root = os.path.dirname(self.destination)
        if not os.path.exists(destination_root):
            try:
                os.makedirs(destination_root)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

        frame_regex = "%.[0-9]+d"

        # Replace the frame regex with a wildcard for glob
        if frame_regex in self.source:
            self.source = self.source.replace(frame_regex, "[0-9].*")

        source_files = glob.glob(self.source)

        self.ffmpeg_input_file_path = "/".join([self.temp_dir, self.full_name, "ffmpeg_input.txt"])

        root = os.path.dirname(self.ffmpeg_input_file_path)
        if not os.path.exists(root):
            try:
                os.makedirs(root)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

        with open(self.ffmpeg_input_file_path, "w") as f:
            for source_file in source_files:
                f.write("file '{}'\n".format(source_file))

    def run(self):
        """ executes an FFMPEG command to concatenate the quicktimes together.
        """

        success = True

        ffmpeg_command = [
            self.ffmpeg_executable,
            "-f", "concat",
            "-safe", "0",
            "-i", self.ffmpeg_input_file_path,
            "-c", "copy",
            self.destination,
            "-nostdin", # Disable interactive mode
            "-y" # Overwrite a file if it exists
        ]

        print("FFMPEG Command: \n")
        print(" ".join(ffmpeg_command))
        print("\n")

        process = subprocess.Popen(ffmpeg_command, shell=False)
        process.communicate()

        # Success if return code is 0
        success = process.returncode == 0

        if success:
            print("Successfully concatenated movs to: \n{}".format(self.destination))
            return 0
        else:
            print("FAILED to concatenate movs to: \n{}".format(self.destination))
            return 1
