import collections
import copy
import datetime
import logging
import os
import six
import traceback


from weakref import WeakKeyDictionary

from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.task_exceptions import TaskException, TaskValidationException

class SequenceTask(Task):
    """ Base task for all sequence tasks. Will run method for each frame in the 
        frame range. 
        Export method will generate multiple tasks based on chunk_size. 0 for no chunking.
    """
    start_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int, required=True, 
        description="frame to start the task from.")
    end_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int, required=True, 
        description="frame to end the task from.")
    chunk_size = TaskAttribute(default_value=8, configurable=True, attribute_type=int, 
        description="Number of frames to split each task into for running on multiple machines. 0 to perform no chunking")

    def __init__(self, **kwargs):
        """ Initializes Task object
        """
        super(SequenceTask, self).__init__(**kwargs)

    def validate(self):
        """ Validates the frame range, and chunk size parameters.

            Raises:
                TaskValidationException: Invalid frame range
                TaskValidationException: Invalid Chunk size
        """

        super(SequenceTask, self).validate()

        if self.chunk_size < 0:
            raise TaskValidationException("Chunk size must be a positive number")

        if self.end_frame < self.start_frame:
            raise TaskValidationException("Invalid Frame Range: {start_frame} - {end_frame}".format(
                    self.end_frame, 
                    self.start_frame
                )
            )

        if self.end_frame < 0 or self.start_frame < 0:
            raise TaskValidationException("Invalid Frame Range (Negative frame numbers not allowed): {start_frame} - {end_frame}".format(
                    self.end_frame, 
                    self.start_frame
                )
            )

    def export_to_command_line(self, temp_dir=None, deadline=False):
        """ Will generate a `wolfkrow_run_task` command line command to run in order to 
            re-construct and run this task via command line. 
                Note: Intended to be used on deadline. The "<START_FRAME>" and 
                "<END_FRAME>" tokens are replaced by deadline.
        """

        if not self.temp_dir:
            self.temp_dir = temp_dir

        arg_str = ""
        for attribute_name, attribute_obj  in self.task_attributes.items():
            if attribute_obj.serialize is False:
                continue

            value = attribute_obj.__get__(self)
            if value is None:
                continue
            elif deadline and attribute_name == "start_frame":
                value="<STARTFRAME>"
            elif deadline and attribute_name == "end_frame":
                value = "<ENDFRAME>"

            # These types can have spaces in the "repr" output, so convert them 
            # to strings so that they are wrapped in quotes on the command line.
            if (isinstance(value, dict) or
                isinstance(value, list) or
                isinstance(value, set)):

                value = repr(value)

            arg_str = "{arg_str} --{attribute_name} {value}".format(
                arg_str=arg_str,
                attribute_name=attribute_name,
                value=repr(value)
            )

        command = "{executable} {executable_args} --task_name {task_type} {task_args}".format(
            executable=self.command_line_executable, 
            executable_args= self.command_line_executable_args or "",
            task_type=self.__class__.__name__, 
            task_args=arg_str
        )

        return [(self, command)]

    def export_to_python_script(self, job_name, temp_dir=None):
        """ Will Export this task into a stand alone python script to allow for synchronous 
            execution of many tasks among many machines. This is intended to be used 
            alongside a distributed render manager (Something like Tractor2, or deadline).
            
            Note: This a fairly generic implementation that takes advantage of 
                __repr__ on each task, then does some logic to determine imports 
                required, then writes a .py file that can be executed on its own 
                to execute this task.

            Args:
                job_name (str): name of the job this task is a part of. Only used in generation of the scripts name.

            Kwargs:
                temp_dir (str): temp directory to write the stand alone python script to.

            returns:
                (str) - The file path to the exported task.
        """

        # If the chunk_size is 0, then we just do a normal export.
        if self.chunk_size == 0:
            return super(SequenceTask, self).export_to_python_script(temp_dir=temp_dir, job_name=job_name)

        tasks = []
        start_frame = self.start_frame
        end_frame = self.end_frame
        name = self.name

        self.end_frame = start_frame - 1
        while self.end_frame < end_frame:

            self.start_frame = self.end_frame + 1
            self.end_frame = min(self.start_frame + self.chunk_size - 1, end_frame) 

            # Update task name so that it is unique
            frame_str = "{}-{}".format(self.start_frame, self.end_frame)
            self.name = "{}_{}".format(name, frame_str)

            framed_task = self.copy()

            exported = Task.export_to_python_script(
                framed_task, 
                job_name=job_name,
                temp_dir=temp_dir, 
            )
            tasks.append(exported)

        self.start_frame = start_frame
        self.end_frame = end_frame
        self.name = name
        return tasks
