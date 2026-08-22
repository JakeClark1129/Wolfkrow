
import re

from Deadline.Plugins import DeadlinePlugin, PluginType
from FranticX.Processes import ManagedProcess

def GetDeadlinePlugin():
    return WolfkrowTask()

def CleanupDeadlinePlugin(plugin):
    plugin.cleanup()

class WolfkrowTask(DeadlinePlugin):
    def __init__(self):
        super().__init__()

        self.InitializeProcessCallback += self.initialize_process
        self.RenderTasksCallback += self.render_tasks

        self.ManagedProcess = None

    def cleanup(self):
        self.CleanupProcess()

        del self.InitializeProcessCallback

        if self.ManagedProcess:
            self.ManagedProcess.Cleanup()
            del self.ManagedProcess

    def initialize_process(self):
        self.PluginType = PluginType.Advanced
        self.StdoutHandling = True
        self.UseProcessTree = True


    def render_tasks(self):
        executable_args = self.GetPluginInfoEntry("ExecutableArgs")
        if executable_args:
            executable_args = [executable_args]

        additional_args = self.GetPluginInfoEntry("AdditionalArgs")
        if additional_args:
            additional_args = [additional_args]
        
        executable = self.GetPluginInfoEntry("Executable")

        task_name = self.GetPluginInfoEntry("TaskName")

        json_args_file = self.GetPluginInfoEntry("JsonArgsFile")

        # Get the start and end frame configured for this plugin.
        start_frame = self.GetPluginInfoEntry("StartFrame")
        end_frame = self.GetPluginInfoEntry("EndFrame")

        # For job chunking, the start and end frame above, will be <START_FRAME> and <END_FRAME>.
        if isinstance(start_frame, str):
            start_frame = re.sub( r"<(?i)STARTFRAME>", str(self.GetStartFrame()), start_frame)
        
        if isinstance(end_frame, str):
            end_frame = re.sub( r"<(?i)ENDFRAME>", str(self.GetEndFrame()), end_frame)

        # Build the command
        command_bits = []

        # Executble args must go first so they are passed to the executable directly (typically Python)
        if executable_args:
            command_bits += executable_args

        # Next, we add any frame range information.
        # NOTE: It is important that the start and end frame args are not the last
        #   args. This is because sometimes the executable will be Nuke, and Nuke
        #   consumes any numbers at the the end of the command line as it's own
        #   internal arguments.
        if start_frame is not None and end_frame is not None:
            command_bits += [
                "--start_frame", str(start_frame),
                "--end_frame", str(end_frame), 
            ]

        # Next, add the name of the Task to use for execution
        if task_name:
            command_bits += [
                "--task_name", task_name
            ]

        # Next, we add the main json args file.
        if json_args_file:
            command_bits += [
                "--json_args_file", json_args_file
            ]

        # And Finally, allow any other arbitrary args. This gives us enough flexibility 
        # to bypass a normal python executable, and the wolfkrow_run_task script 
        # if needed, and just call some other executable with custom args.
        if additional_args:
            command_bits += additional_args

        print("Executing command:")
        print(" ".join([executable] + command_bits))

        self.managed_process = ShellManagedProcess(self, executable, command_bits)
        self.RunManagedProcess(self.managed_process)

        if self.managed_process.exit_code != 0:
            self.FailRender(f"Wolfkrow Task exited with non-zero exit code: {self.managed_process.exit_code}")

class ShellManagedProcess( ManagedProcess ):
    """ Provides a simple Managed process with progress handling which will be 
    initialized and executed by the WolfkrowTask deadline plugin.
    """
    
    def __init__( self, deadlinePlugin, executable, arguments):
        super().__init__()

        self.deadlinePlugin = deadlinePlugin
        self.executable = executable
        self.arguments = arguments
        self.exit_code = -1

        # Regex uesd to parse the output logs of the wolfkrow task to track the progress.
        self.progress_regex = r".*Progress: (\d+([.]\d+)?)%.*"

        self.InitializeProcessCallback += self.initialize_process
        self.RenderExecutableCallback += self.render_executable
        self.RenderArgumentCallback += self.render_arguments
        self.CheckExitCodeCallback += self.check_exit_code

    def Cleanup( self ):
        for stdoutHandler in self.StdoutHandlers:
            del stdoutHandler.HandleCallback

        del self.InitializeProcessCallback
        del self.RenderExecutableCallback
        del self.RenderArgumentCallback
        del self.CheckExitCodeCallback
    
    def initialize_process(self):
        self.PopupHandling = True
        self.StdoutHandling = True
        self.HideDosWindow = True
        # Ensure child processes are killed and the parent process is terminated on exit
        self.UseProcessTree = True
        self.TerminateOnExit = True

        self.AddStdoutHandlerCallback(self.progress_regex).HandleCallback += self.handle_progress

    def render_executable(self):
        return self.executable

    def render_arguments(self):
        return " ".join(self.arguments)

    def check_exit_code(self, exit_code):
        # Seems to be a bug in Nuke 16 which is introducing this exit code during Nuke Shutdown. 
        # Just Ignore it and we should be fine.
        if exit_code == -1073740940:
            self.exit_code = 0
            self.deadlinePlugin.LogInfo( "Ignoring Nuke 16.0 Shutdown Exit Code -1073740940" )
        else:
            self.exit_code = exit_code

    def handle_progress(self):
        """ Progress handler for Wolfkrow Tasks.

        Similar to the default CommandLine executable, it expects a log like "Progress: 56%"
        And then it will extract the % value, and set the deadline tasks progress 
        on Deadline.
        """
        progress = float(self.GetRegexMatch(1))
        self.deadlinePlugin.SetProgress(progress)
