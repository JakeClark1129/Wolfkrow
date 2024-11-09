


class TaskExport(object):
    def __init__(self, task, executable, executable_args=None, args=None, script=None):
        self.task = task
        self.executable = executable
        self.executable_args = executable_args
        self.task_args = args

        self.script = script

        self.deadline_id = None

    @property
    def command(self):
        return self.executable + ' ' + self.args

    @property
    def args(self):
        args = ""
        if self.executable_args:
            executable_args = " ".join(self.executable_args)
            args += executable_args + " "
        if self.task_args:
            args += self.task_args

        return args