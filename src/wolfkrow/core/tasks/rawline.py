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

class Rawline(SequenceTask):
    """ FileMove Task implementation
    """

    destination = CommandLineArg(
        default_value=None, 
        command_line_arg="--output-path", 
        configurable=True, 
        attribute_type=str, 
        description="The 'path' for the output files. If not specified, the converted files will be written in the directory where the executable has been called."
    )

    base_name = CommandLineArg(
        default_value=None,
        command_line_arg="--base-name", 
        configurable=True,
        description="""Base 'name' for the output files. If not specified, the same 
file name as the input images will be used, with the output format dependent file extension."""
    )

    pad = CommandLineArg(
        default_value=None, 
        command_line_arg="--pad",
        configurable=True,
        description="Specifies the filename padding."
    )

    comment = CommandLineArg(
        default_value=None, 
        command_line_arg="--comment",
        configurable=True,
        description="Specifies a comment string to be written to the file as metadata."
    )

    format = CommandLineArg(
        default_value=None,
        command_line_arg="--format",
        attribute_options=list(range(0, 8)),
        configurable=True,
        description="""Output file format. Default is 1.
    0 = DPX
    1 = EXR
    2 = JPEG
    3 = MayaIFF
    4 = SGI
    5 = TIFF
    6 = QuickTime
    7 = SGO Mistika JS
    8 = OpenDML AVI"""
    )

    transfer_curve = CommandLineArg(
        default_value=None, 
        command_line_arg="--transfer-curve", 
        attribute_options=list(range(0, 12)), 
        configurable=True,
        description="""Transfer curve (aka. Gamma) to use for output files. Default is 0.
     0 = Linear
     1 = Rec709
     2 = sRGB
     3 = Cineon/DPX Log
     4 = Josh Pines Log
     5 = ACEScc
     6 = ACEScct
     7 = ARRI Log C
     8 = RED Log3G10
     9 = Sony S-Log3
    10 = ROMM RGB
    11 = SMPTE ST2084 (PQ)
    12 = Hybrid Log-Gamma (HLG)"""
    )

    colour_space = CommandLineArg(
        default_value=None, 
        command_line_arg="--color-space", 
        attribute_options=list(range(0, 16)), 
        configurable=True,
        description="""Color space to use for output files. Default is 0.
    0 = Camera Native
    1 = Rec709
    2 = sRGB
    3 = Adobe 1998
    4 = Cineon/DPX
    5 = Rec2020
    6 = ACES2065-1 (AP0)
    7 = ACEScg (AP1)
    8 = ALEXA Wide Gamut
    9 = Adobe Wide Gamut
    10 = REDWideGamutRGB
    11 = Sony S-Gamut3
    12 = Sony S-Gamut3.Cine
    13 = ROMM RGB
    14 = Sharp RGB
    15 = DCI-P3
    16 = XYZ"""
    )

    exr_threads = CommandLineArg(
        default_value=None, 
        command_line_arg="--exr-threads", 
        attribute_options=list(range(0, 12)), 
        configurable=True,
        description="Number of OpenEXR encoder threads. Default is 1. Range is 1 - 12."
    )
    
    source = CommandLineArg(
        default_value=None, 
        required=True,
        configurable=True, 
        description="The path to the file to convert."
    )

    additional_arguments = TaskAttribute(
        default_value=[],
        attribute_type=list,
        configurable=True,
        description="Any additional arguments to be supplied that are not already supported by this task."
    )

    def __init__(self, **kwargs):
        """ Initialize the Rawline Object

            Args:
        """
        super(Rawline, self).__init__(**kwargs)

    def validate(self):
        """ Preforms Validation checks to ensure the Rawline Task is properly initialized.

            Raises:
                TaskValidationException: Rawline task is not properly initialized
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

    def _compile_command_line(self, frame):

        command_args = []
        for attr_name in self.task_attributes:
            attr = self.task_attributes[attr_name]

            # Only compile the command line args.
            if not isinstance(attr, CommandLineArg):
                continue
            if attr_name == "source":
                continue

            value = attr.__get__(self)
            if value is not None:
                if attr.command_line_arg != "":
                    command_args.append(attr.command_line_arg)
                command_args.append(str(value))

        command_args.extend(self.additional_arguments)

        return command_args

    def run(self):
        """ execute Rawline with the given arguments.
        """

        success = True
        failed_frames = []
        # rawline has a weird way of rendering sequences. Just call it once per 
        # frame instead and set the start frame to the current frame each time.
        for frame in range(self.start_frame, self.end_frame + 1):
            command_line = ["RAWline", "--start-frame", str(frame)]
            command_line.extend(self._compile_command_line(frame))
        
            # Replace the '%d' token in the source path with the current frame
            try:
                source = self.source % frame
            except TypeError as error:
                # Warn that the source path does not support the current frame.
                source = self.source
                print("Warning: Source path '{}' is not a frame sequence.".format(source))

            command_line.append(source)

            print("command: " + str(command_line))

            process = subprocess.Popen(command_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
            stdout, stderr = process.communicate()
            print(stdout)
            print(stderr)
            if process.returncode != 0:
                success = False
                failed_frames.append(frame)

        failed_frame_str = ""
        for frame in failed_frames:
            failed_frame_str = failed_frame_str + str(frame) + ", "

        failed_frame_str = failed_frame_str.rstrip(", ")

        if not success:
            print("Failed for frames: {}".format(failed_frame_str))
        return 0 if success else 1
