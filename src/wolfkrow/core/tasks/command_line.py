""" Module implementing the FileCopy task.
"""

import errno
import os
import shutil

from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.file_operation import FileOperation
from wolfkrow.core.tasks.task_exceptions import TaskValidationException

class CommandLine(Task):
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
    """

    script = TaskAttribute(required=True, description="The Command to run on the command line.")
    args = TaskAttribute(required=True, attribute_type=list, description="The arguments to the command. Must be supplied as a list.")

    def export_to_command_line(self, deadline=False):
        """ Overwrites the default behavior of this this method to just recreate 
            the command line script to run from the script and args attributes.

            We don't need Wolfkrow to act as a middle man here...
        """

        arg_str = " ".join(self.args)

        command = "{script} {script_args}".format(
            script=self.script, 
            script_args=arg_str
        )

        return (self, command)
