""" Module implementing the FileCopy task.
"""

import errno
import os
import shutil

from wolfkrow.core.engine.task_export import TaskExport
from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.file_operation import FileOperation
from wolfkrow.core.tasks.task_exceptions import TaskValidationException
from wolfkrow.core.tasks.sequence_task import SequenceTask
from wolfkrow.core.engine.resolver import Resolver


class CommandLine(SequenceTask):
    """ Allows execution of arbitrary command line scripts.

        Note: Allowing execution of command line scripts this way has some 
            potential security issues. However, Tasks are executed as the user 
            that is running this workflow. So the user running will need to have
            permissions to do anything bad (Not just any user can run `rm -rf /*`). 
            (Which they would be able to do anyway if they had malicious intent)

            The risk here is if someone with malicious intent modifies the 
            workflow configuration, and then the workflow is executed by a user 
            who has the permissions to actually do some damage. IE: Malicious user
            modifies the config to be `download_malware_script`, then a user with
            elevated permissions runs this.

            Also, since the Workflow would be run as someone else, there would be
            no way of identifying the malicious individual. (Unless a changelog is
            kept on the configuration file)

        TODO: What are some potential solutions to the security issues with this?
            1) Have an WOLFKROW_WHITELIST_SCRIPTS environment variable (or config 
                entry) which whitelists scripts that are allowed to be executed.

        To execute this as a sequence task, include {start_frame} and {end_frame}
        string tokens as part of the args list. The export will then substitute 
        the start and end frame attributes for their corresponding tokens.
    """

    script = TaskAttribute(required=True, description="The Command to run on the command line.")
    args = TaskAttribute(required=True, attribute_type=list, description="The arguments to the command. Must be supplied as a list.")

    def export_to_command_line(self, job_name, temp_dir=None, deadline=False, export_json=False):
        """ Overwrites the default behavior of this method to just recreate 
            the command line script to run from the script and args attributes.

            We don't need Wolfkrow to act as a middle man here...
        """

        args = self.args.copy() # Dont change the original args list.

        if self.start_frame and self.end_frame:
            
            start_frame = self._command_line_sanitize_attribute("start_frame", self.start_frame, deadline=deadline)
            end_frame = self._command_line_sanitize_attribute("end_frame", self.end_frame, deadline=deadline)
            
            replacements = {
                "start_frame": start_frame,
                "end_frame": end_frame,
            }
            resolver = Resolver(replacements, None)
            
            for index, arg in enumerate(self.args):
                try:
                    arg = resolver.resolve(arg)
                except IndexError as e:
                    pass
                except KeyError as e:
                    pass
                finally:
                    args[index] = arg

        task_export = TaskExport(
            self,
            executable=self.script, 
            executable_args=args,
            args="",
        )

        return [task_export]

    # TODO: We need to implement the run method, otherwise the PythonScript export 
    # type won't work for this task type. It should be a subprocess call.
