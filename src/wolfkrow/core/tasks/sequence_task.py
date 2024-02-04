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
    start_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int, required=False, 
        description="frame to start the task from.")
    end_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int, required=False, 
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

        # If there is no start frame or end frame, then we don't need to do any of the following checks.
        if self.start_frame is None and self.end_frame is None:
            pass
        elif self.start_frame is None and self.end_frame is not None:
            raise TaskValidationException("Start frame specified, but end frame "
                "not specified. {} - {}".format(self.start_frame, self.end_frame)
            )

        elif self.end_frame is None and self.start_frame is not None:
            raise TaskValidationException("End frame specified, but start frame "
                "not specified. {} - {}".format(self.start_frame, self.end_frame)
            )
        else:
            if self.chunk_size < 0:
                raise TaskValidationException("Chunk size must be a positive number")


            if self.end_frame < self.start_frame:
                raise TaskValidationException("Invalid Frame Range: {start_frame} - {end_frame}".format(
                        self.end_frame, 
                        self.start_frame
                    )
                )

            if self.end_frame < 0 or self.start_frame < 0:
                raise TaskValidationException("Invalid Frame Range (Negative frame "
                    "numbers not allowed): {start_frame} - {end_frame}".format(
                        start_frame=self.start_frame,
                        end_frame=self.end_frame, 
                    )
                )

    def _command_line_sanitize_attribute(self, attribute_name, attribute_value, deadline=False):
        """ Processes the attribute value to prepare it for use on the command line.

            Does additional processing to prepare the attribute for use on deadline.
        """

        value = super(SequenceTask, self)._command_line_sanitize_attribute(
            attribute_name,
            attribute_value,
            deadline=deadline
        )

        if deadline and attribute_name == "start_frame":
            value="<STARTFRAME>"
        elif deadline and attribute_name == "end_frame":
            value = "<ENDFRAME>"

        return value

    def _generate_bash_script_contents(self, temp_dir=None, deadline=False):
        """ Overrides the default generate bash script method in order to tweak
        the bash scripts generated for use on deadline.
        """

        bash_scripts = super(SequenceTask, self)._generate_bash_script_contents(temp_dir=temp_dir, deadline=deadline)

        if deadline and self.start_frame is not None and self.end_frame is not None:
            for index, (task, bash_script) in enumerate(bash_scripts):
                # Replace deadlines <STARTFRAME> and <ENDFRAME> tokens in the bash 
                # script with "$1" and "$2" because deadline we are modifying the 
                # bash script so that deadline will pass the start and end frames 
                # into the script.
                bash_script = bash_script.replace("<STARTFRAME>", "$1")
                bash_script = bash_script.replace("<ENDFRAME>", "$2")
                bash_scripts[index] = (task, bash_script)

        return bash_scripts

    def _export_sequence_task(self, export_method_name, export_method_args):
        """ Will split the given task into chunks by the frame range and export a task for each export.
            Or falls back to the default export process in some circumstances.

        Args:
            export_method_name (str): The name of the method to use to export the task.
                Eg: "export_to_command_line", "export_to_python_script", etc...
            export_method_args (dict): Arg dict to give to the export method.
        """
        # Check if there is a deadline property passed into the export method.
        deadline = export_method_args.get("deadline", False)

        # If we are exporting for deadline, then we just want to use the regular
        # export because deadline handles the chunking for us.
        # OR
        # Use the regular export if chunk size is 0 or if there is no start or end frame.
        if deadline or (self.start_frame is None or self.end_frame is None or self.chunk_size == 0):
            export_method = getattr(super(SequenceTask, self), export_method_name)
            exported = export_method(**export_method_args)
            return exported

        # Otherwise we export the task into chunked tasks
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

            # NOTE: Potential gotcha! We are creating a shallow copy here, which 
            # means that changing the value of any mutable attributes on this copy 
            # will affect ALL copies of this task. Change this to a deep_copy if 
            # we want to modify mutable data types
            framed_task = self.copy()

            export_method = getattr(super(SequenceTask, framed_task), export_method_name)

            exported = export_method(**export_method_args)
            tasks.extend(exported)

        self.start_frame = start_frame
        self.end_frame = end_frame
        self.name = name
        return tasks


    def export_to_command_line(self, temp_dir=None, deadline=False):
        """ Will generate a `wolfkrow_run_task` command line command to run in order to 
            re-construct and run this task via command line. 

            Args:
                temp_dir (str): temp directory to write the stand alone python script to.
                deadline (bool): whether or not to prepare this task for deadline.
        """

        # We have a framed sequence task, so export the chunked tasks
        export_method_name = "export_to_command_line"
        export_method_args = {
            "temp_dir": temp_dir, 
            "deadline": deadline
        }
        exported = self._export_sequence_task(
            export_method_name,
            export_method_args,
        )

        return exported

    def export_to_bash_script(self, job_name, temp_dir=None, deadline=False):
        """ Uses the standard export to command line method, then writes that to 
        a bash script.

        Args:
            job_name (str): name of the job this task is a part of. Only used in generation of the scripts name.

        Kwargs:
            temp_dir (str): temp directory to write the stand alone python script to.
            deadline (bool): whether or not to prepare this task for deadline.
        """

        # We have a framed sequence task, so export the chunked tasks
        export_method_name = "export_to_bash_script"
        export_method_args = {
            "job_name": job_name,
            "temp_dir": temp_dir,
            "deadline": deadline,
        }
        exported = self._export_sequence_task(export_method_name, export_method_args)

        if deadline and self.start_frame and self.end_frame:
            # Add Start and End frame tokens to the export for sequence tasks.
            for index, export in enumerate(exported):
                task, script_path = export
                script_path = "{script_path} <STARTFRAME> <ENDFRAME>".format(script_path=script_path)
                exported[index] = (task, script_path)

        return exported

    def export_to_python_script(self, job_name, temp_dir=None, deadline=False):
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

        # We have a framed sequence task, so export the chunked tasks
        export_method_name = "export_to_python_script"
        export_method_args = {
            "job_name": job_name, 
            "temp_dir": temp_dir
        }
        exported = self._export_sequence_task(export_method_name, export_method_args)

        if deadline and self.start_frame and self.end_frame:
            # Add Start and End frame tokens to the python script args for sequence tasks.
            for index, export in enumerate(exported):
                task, script_path = export
                script_path = "{script_path} <STARTFRAME> <ENDFRAME>".format(script_path=script_path)
                exported[index] = (task, script_path)
        return exported
