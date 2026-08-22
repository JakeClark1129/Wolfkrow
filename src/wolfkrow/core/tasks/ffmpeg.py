""" Module implementing the FileCopy task.
"""
from __future__ import print_function

from builtins import str
from builtins import range
import errno
import os
import shutil
import subprocess

from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.sequence_task import SequenceTask
from wolfkrow.core.tasks.task_exceptions import TaskValidationException


class CommandLineArg(TaskAttribute):
    def __init__(self, command_line_arg="", **kwargs):
        super(CommandLineArg, self).__init__(**kwargs)
        self.command_line_arg = command_line_arg

class FFMPEG(SequenceTask):
    """ FileMove Task implementation
    """

    source = CommandLineArg(
        default_value=None, 
        command_line_arg="-i",
        required=True,
        configurable=True, 
        description="The path to the file to convert."
    )

    destination = TaskAttribute(
        default_value=None, 
        configurable=True, 
        attribute_type=str, 
        description="The 'path' for the output files. If not specified, the converted files will be written in the directory where the executable has been called."
    )

    additional_arguments = TaskAttribute(
        default_value=[],
        attribute_type=list,
        configurable=True,
        description="Any additional arguments to be supplied that are not already supported by this task."
    )

    overwrite = TaskAttribute(
        default_value=False, 
        attribute_type=bool,
        configurable=True,
        description="Whether or not to overwrite the destination file if it exists."
    )

    inputs = ["input_sequence", "start_frame", "end_frame"]
    outputs = ["input_sequence", "start_frame", "end_frame"]

    def __init__(self, **kwargs):
        """ Initialize the FFMPEG Object

            Args:
        """
        super(FFMPEG, self).__init__(**kwargs)

    def validate(self):
        """ Preforms Validation checks to ensure the FFMPEG Task is properly initialized.

            Raises:
                TaskValidationException: FFMPEG task is not properly initialized
        """

        for attr_name, attr in list(self.task_attributes.items()):
            if attr.required is True and getattr(self, attr_name) is None:
                
                raise TaskValidationException("Required argument {arg} not supplied.".format(
                    arg=attr_name
                ))

    def setup(self):
        """ Created output directory for the converted EXR files.
        """
        if not os.path.exists(self.destination):
            try:
                os.makedirs(self.destination)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

    def _compile_command_line(self):

        command_args = []
        for attr_name in self.task_attributes:
            attr = self.task_attributes[attr_name]

            # Only compile the command line args.
            if not isinstance(attr, CommandLineArg):
                continue
            if attr_name == "destination":
                continue

            value = attr.__get__(self)
            if value is not None:
                if attr.command_line_arg != "":
                    command_args.append(attr.command_line_arg)
                command_args.append(str(value))

        command_args.extend(self.additional_arguments)

        return command_args

    def call_ffmpeg(self, source, destination):

        command_line = [self.command_line_executable]
        command_line.extend(self._compile_command_line())
        command_line.append("-nostdin") # Disable interactive move in ffmpeg
        if self.overwrite:
            command_line.append("-y") # Overwrite a file if it exists
        command_line.append(destination)

        print("command: " + str(command_line))
        process = subprocess.Popen(command_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        stdout, stderr = process.communicate()
        print(stdout)
        print(stderr)

        # Success if return code is 0
        success = process.returncode == 0
        return success

    def run(self):
        """ execute FFMPEG with the given arguments.
        """

        success = True
        failed_frames = []
        # rawline has a weird way of rendering sequences. Just call it once per 
        # frame instead and set the start frame to the current frame each time.
        if self.start_frame is not None and self.end_frame is not None:
            for frame in range(self.start_frame, self.end_frame + 1):
                # Replace the '%d' token in the source path with the current frame
                try:
                    source = self.source % frame
                    destination = self.destination % frame
                except TypeError as error:
                    source = self.source
                    destination = self.destination

                command_success = self.call_ffmpeg(source, destination)
                if not command_success:
                    success = False
                    failed_frames.append(frame)
        else:
            command_success = self.call_ffmpeg(self.source, self.destination)
            if not command_success:
                success = False
                failed_frames.append(self.source)


        failed_frame_str = ""
        for frame in failed_frames:
            failed_frame_str = failed_frame_str + str(frame) + ", "

        failed_frame_str = failed_frame_str.rstrip(", ")

        if not success:
            print("Failed for frames: {}".format(failed_frame_str))
        return 0 if success else 1

    @classmethod
    def ui_settings(cls):
        return {
            "appear_in_task_list": True,
            "icon": None # TODO: Add a default icon
        }