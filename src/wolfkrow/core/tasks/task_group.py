""" Module implementing a group of tasks.
"""

import errno
import logging
import os

from .task import Task, TaskAttribute
from .sequence_task import SequenceTask
from .task_exceptions import TaskValidationException

class TaskGroup(Task):
    """ TaskGroup Task implementation. Will accept a list of Task names that it 
    then constructs from the wolfkrow config files.

    This Task overrides the default export method, and instead manually handles 
    the export of its grouped tasks. It then takes the export of each Task and 
    combines it into a single file, which can then be executed. 

    NOTE: Tasks will get executed in the order that they are specified in the
        task_names attribute.

    For PythonScript export type, the export is the file path to an executable .py file

    For CommandLine export type, the export is a bash command which runs a bash 
    script containing all the grouped tasks exported commands.

    """

    task_names = TaskAttribute(
        default_value=[], 
        configurable=True, 
        attribute_type=list, 
        description="list of Task names from the wolfkrow.yaml files to construct "
            "and apend together in a script. Tasks will get executed in the "
            "order that they are specified here."
    )

    def _write_python_group_file(self, file_handle, exported_tasks):
        """ Writes a task exported via the PythonCommand method to the file_handle
        provided. 

        Args:
            file_handle (File): Opened File handle to write to. Calling code is 
                responsible for cleaning up the file_handle afterwards.
            exported_tasks (List): A list of all the exported tasks.
        """
        # Write a shebang which will call python. This will most likely go unused,
        # since the python executable to use is explicitly set later.
        file_handle.write("#! /usr/bin/env python\n\n")

        file_handle.write("import sys\n\n")

        # Add an "all_success" variable to use as the return value in the end.
        file_handle.write("all_success = 0\n\n")

        # Iterate over all of the exported tasks.
        for exported_task, export_str in exported_tasks:
            # Open the python file pointed to by the export_str
            # See Task.export_to_python_script method for exported python script logic.
            with open(export_str, "r") as fh:
                content = fh.readlines()

            # Strip the first and last line of the python file because they are 
            # calling "import sys" and "sys.exit" which we don't want.
            content = content[2:-1]

            # Modify the content list so that is set the "all_success" variable 
            # based on return value.
            content.append("if ret != 0:\n")
            content.append("    all_success = 1\n\n")

            # Now write each line back to the group file.
            for line in content:
                file_handle.write(line)

        file_handle.write("sys.exit(all_success)")

    def _write_command_line_group_file(self, file_handle, exported_tasks):
        """ Writes a task exported via the CommandLine method to the file_handle
        provided.

        Args:
            file_handle (File): Opened File handle to write to. Calling code is 
                responsible for cleaning up the file_handle afterwards.
            exported_tasks (List): A list of all the exported tasks.
        """
        
        # Write a shebang which will call bash. This will most likely go unused,
        # since the executable to use is explicitly set later.
        file_handle.write("#! /usr/bin/env bash\n\n")

        for exported_task, export_str in exported_tasks:
            # Write the command to the bash file. This one is simple because the 
            # export_str should already be a bash command, so simply writing it 
            # to the file is enough.
            file_handle.write(export_str)
            file_handle.write("\n\n")

    def _write_group_file(self, export_type, exported_tasks, group_file_path):
        """ Writes all of the exported tasks to a single file which can be executed
        on the farm.

        Args:
            export_type (str): The export type which was used to export the tasks.
            exported_tasks (list): A list of all the exported tasks.
            group_file_path (str): The file path to the write the combined tasks to.
                This is the file path which will get executed later.
        """

        with open(group_file_path, "w") as fh:
            if export_type == "PythonScript":
                self._write_python_group_file(fh, exported_tasks)
            elif export_type == "CommandLine":
                self._write_command_line_group_file(fh, exported_tasks)
            elif export_type == "BashScript":
                # TODO: Implement this
                raise TaskValidationException("Unsupported Export Type received: {}".format(export_type))
            else:
                raise TaskValidationException("Unsupported Export Type received: {}".format(export_type))

    def export(self, export_type, temp_dir=None, job_name=None, deadline=False):
        """ Overrides the default export method to allow it to combine all of the
        tasks configured into a single file which can be executed later on.

        Args:
            export_type (str): The export method to use to export the grouped tasks.

        Kwargs:
            temp_dir (str): temp directory used to write the grouped task bash file.
            job_name (str): Passed onto the PythonScript export method. Used to 
                choose the name of the exported python script.
            deadline (bool): whether or not to prepare the exported tasks for deadline.
                TODO: This arguement seemingly does nothing... Lets remove it.
        """
        self.validate()

        from ...builder.workflow_builder import Loader

        # Assign the temp_dir variable so that the tempdir is available after submission.
        if self.temp_dir is None:
            self.temp_dir = temp_dir

        # Initialize the loader so that we can load our tasks from the configuration.
        loader = Loader(
            config_file_paths=self.config_files,
            replacements=self.replacements,
            temp_dir=self.temp_dir,
            sgtk=self.sgtk,
        )

        # Load the tasks from the configuration
        tasks_to_export = loader.tasks_from_task_names_list(self.task_names)

        # Now export each task, and append to a list containing all the exported tasks.
        # NOTE: Tasks will get executed in the order that they are exported in.
        exported_tasks = []
        for task in tasks_to_export:
            # We cannot group tasks which are sequence tasks due to the way that 
            # they get run on deadline. They rely on a "<STARTFRAME>" and "<ENDFRAME>"
            # token which gets passed into the same task arg list multiple times.
            # This goes against the very nature of the group tasks, because the 
            # task should only be run a single time.
            # TODO: It may be possible to still get sequence tasks to work, but 
            # we would need to disable chunking for the export, and sub the <STARTFRAME> 
            # <ENDFRAME> tokens manually.
            if deadline and isinstance(task, SequenceTask):
                raise TaskValidationException("Cannot group Sequence tasks when executing on deadline.")

            exported_tasks_ = task.export(
                export_type, 
                temp_dir=temp_dir, 
                job_name=job_name, 
                deadline=deadline
            )
            exported_tasks.extend(exported_tasks_)

        group_path_extension = ".py" if export_type == "PythonScript" else ".bash"

        # Determine the file path to the group output file.
        group_file_path = os.path.join(temp_dir, self.name + group_path_extension)

        # Write the exported tasks to the grouped task output file.
        self._write_group_file(export_type, exported_tasks, group_file_path)

        # The task graph expects different outputs based on the export type.
        if export_type == "CommandLine":
            export_command = "bash " + group_file_path
        elif export_type == "PythonScript":
            export_command = group_file_path
        elif export_type == "BashScript":
            # TODO: Implement this
            raise TaskValidationException("Unsupported Export Type received: {}".format(export_type))
        else:
            raise TaskValidationException("Unsupported Export Type received: {}".format(export_type))


        return [(self, export_command)]
