


class TaskExport(object):
    def __init__(self, task, executable, executable_args=None, args=None):
        self.task = task
        self.executable = executable
        self.executable_args = executable_args
        self.task_args = args

        self.deadline_id = None

    @property
    def command(self):
        """ Calculates and returns the complete command.

        Returns:
            str: The complete command
        """
        return self.executable + ' ' + self.args

    @property
    def args(self):
        """ Calculates and returns the complete argument list. 

        Returns:
            str: The complete argument string
        """
        args = ""
        if self.executable_args:
            executable_args = " ".join(self.executable_args)
            args += executable_args + " "
        if self.task_args:
            args += self.task_args

        return args

    def as_list(self):
        """ Returns the args as a list rather than a string. """

        args = []
        
        if self.executable_args:
            args.extend(self.executable_args)
            
        # TODO: This will break if an argument has a space in it.
        if self.task_args:
            args.extend(self.task_args.split())

        return args