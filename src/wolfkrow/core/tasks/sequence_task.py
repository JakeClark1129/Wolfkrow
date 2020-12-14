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
        Export method will generate multiple tasks based on chunk_size
    """
    start_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int, required=True, 
        description="frame to start the task from.")
    end_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int, required=True, 
        description="frame to end the task from.")
    chunk_size = TaskAttribute(default_value=8, configurable=True, attribute_type=int, 
        description="Number of frames to split each task into when")

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


    def __call__(self):
        """ Validates, sets up, then calls run for each frame in frame range.

            Returns:
                True: If successfully completed
                False: If unsuccessfully completed

            Raises:
                TaskValidationException: Invalid task configuration.
        """

        self.setup()
        try: 
            failed_frames = []
            success = 0
            for frame in range(self.start_frame, self.end_frame + 1):
                result = self.run(frame)
                if not result:
                    success = 1
                    failed_frames.append(frame)
        except Exception as e:
            traceback.print_exc()
            logging.error("Run method for task '%s' Failed. Reason: %s" % (self.name, e))
            return 1

        if success != 0:
            logging.error("Run method for task '%s' Failed for frames: {failed_frame}.".format(self.name, failed_frames))

        return success

    def run(self, frame):
        """ Abstract method for the work that should be done by this Task Object.

            Args:
                frame (int): Current frame to execute the task for.

            Returns:
                True: If successfully completed
                False: If unsuccessfully completed
        """

        raise NotImplementedError("run method must be overridden by child class")

    def export(self, temp_dir, job_name):
        """ Will Export this task into a stand alone python script to allow for synchronous 
            execution of many tasks among many machines. This is intended to be used 
            alongside a distributed render manager (Something like Tractor2, or deadline).
            
            Note: This a fairly generic implementation that takes advantage of 
                __repr__ on each task, then does some logic to determine imports 
                required, then writes a .py file that can be executed on its own 
                to execute this task.

            Args:
                temp_dir (str): temp directory to write the stand alone python script to.
                job_name (str): name of the job this task is a part of. Only used in generation of the scripts name.

            returns:
                (str) - The file path to the exported task.
        """

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
            exported = Task.export(framed_task, temp_dir, job_name)
            tasks.append(exported)

        self.start_frame = start_frame
        self.end_frame = end_frame
        self.name = name
        return tasks
