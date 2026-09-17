


class TaskExport(object):
    def __init__(self, 
        task, 
        executable, 
        executable_args=None, 
        json_args_file=None,
        start_frame=None, 
        end_frame=None, 
        args=None
    ):
        self.task = task
        self.executable = executable
        self.executable_args = executable_args

        self.json_args_file = json_args_file

        self.start_frame = start_frame
        self.end_frame = end_frame

        self.additional_args = args

        self.deadline_id = None

    @property
    def command(self):
        """ Calculates and returns the complete command.

        Returns:
            str: The complete command
        """

        command_bits = self.as_list()
        return " ".join(command_bits)

    @property
    def args(self):
        """ Calculates and returns the complete argument list. 

        Returns:
            str: The complete argument string
        """

        command_bits = self.as_list()
        return " ".join(command_bits[1:])

    def as_list(self):
        """ Returns the command as a list suitable for subprocess calls."""

        command_bits = []

        # Add the main executable first.
        command_bits.append(self.executable)

        # Executble args must go first so they are passed to the executable directly (typically Python)
        if self.executable_args:
            command_bits += self.executable_args

        # Next, we add any frame range information.
        # NOTE: It is important that the start and end frame args are not the last
        #   args. This is because sometimes the executable will be Nuke, and Nuke
        #   consumes any numbers at the the end of the command line as it's own
        #   internal arguments.
        if self.start_frame is not None and self.end_frame is not None:
            command_bits += [
                "--start_frame", str(self.start_frame),
                "--end_frame", str(self.end_frame), 
            ]

        # Next, we add the main json args file.
        if self.json_args_file:
            command_bits += [
                "--json_args_file", self.json_args_file
            ]

        # And Finally, allow any other arbitrary args. This gives us enough flexibility 
        # to bypass a normal python executable, and the wolfkrow_run_task script 
        # if needed, and just call some other executable with custom args.
        if self.additional_args:
            command_bits += self.additional_args

        return command_bits
