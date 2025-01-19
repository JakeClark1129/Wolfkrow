from __future__ import print_function

from builtins import str
from past.builtins import basestring
from builtins import object
import ast
import collections
import copy
import datetime
import errno
import json
import logging
import os
import textwrap
import traceback

from weakref import WeakKeyDictionary

from wolfkrow.core.engine.resolver import Resolver
from wolfkrow.core.engine.task_export import TaskExport
from wolfkrow.core.tasks.task_exceptions import TaskException
from future.utils import with_metaclass



class TaskAttribute(object):
    """ A Descriptor Class intended for use with Task Objects. Using these descriptor objects allows us to store metadata about each attribute 
        on a Task, such as what the type should be, and whether or not it should show up as a configurable attribute on the workflow designer.
    """

    def __init__(self, default_value=None, configurable=False, attribute_options=None, 
        attribute_type=None, required=False, auto_resolve=True, serialize=True, description=None):
        """ Initialize the TaskAttribute object.
        
            Kwargs:
                default_value (any): The default value of the attribute
                configurable (bool): Whether or not this attribute should show up 
                    as a configurable attribute in the workflow designer.
                attribute_options (list): List of accepted values for the attribute.
                attribute_type (Type): Expected type of the value received.
                required (bool): Whether or not this attribute is required for execution.
                serialize (bool): Whether or not this attribute gets included in 
                    the __repr__ output, and therefore included in the exported 
                    task. (See Task.export())
                description (str): Description of this attribute. (Used in the tool tip in the workflow designer.)
        """

        # Must be a WeakKeyDictionary to allow garbage collection to clean up our 
        # tasks when we are done with them. (Not that this matters because this 
        # program will typically be short lived, and the memory used by TaskAttribute 
        # objects will be minimal. Also, Tasks will typically live for the entire 
        # duration of the program)

        # WARNING: Using the WeakKeyDictionary opens us up to some very hard to 
        # debug issues. If garbage collection cleans up one of our TaskAttribute 
        # objects, it will also get removed from this dictionary. If this happens 
        # while we are iterating through the dictionary, then weird stuff can happen. 
        # (Meaning don't iterate through this dictionary!)
        self.data = WeakKeyDictionary()

        self.default_value = default_value
        self.configurable = configurable
        self.attribute_options = attribute_options
        self.attribute_type = attribute_type
        self.serialize = serialize
        self.description = description
        self.required = required
        self.auto_resolve = auto_resolve

    def __get__(self, instance, instance_type=None, dont_resolve=False):
        """ Getter function. Will return the stored value for the specified instance
            if it exists, otherwise it will return the default_value
        """

        if instance is not None:
            # default_value is initialized once when a tasks module is imported. 
            # If default_value is a mutable type (list, dict, etc...), then all 
            # instances of the task will share the same object, meaning that an 
            # update to the value of the TaskAttribute will update all instances
            # of the same Task type.
            # Create a deepcopy of the default value so we always get a unique 
            # object
            data = self.data.get(instance)
            if data is None:
                data = copy.deepcopy(self.default_value)
                # Also assign it so the next time we retrieve this object, we get 
                # our copy, rather than a new fresh copy.
                self.data[instance] = data

            # Only resolve if we:
            #     1. Have data to resolve
            #     2. Are told to resolve
            #     3. Have a resolver to resolve with
            if (data 
                and self.auto_resolve is True 
                and dont_resolve is False 
                and hasattr(instance, "resolver")
            ):
                data = self.resolve(instance, data)

            return data
        else:
            # If we get this attribute from the class level, then we return the 
            # descriptor object instead of an object level value, This allows us 
            # to easily get a reference to the descriptor object. (Which allows 
            # us to access the metadata about this attribute easily)
            return self

    def __set__(self, instance, value):
        """ Setter function. Will set the given value in the data dictionary using 
            the instance as the key in the dictionary.
        """

        # Don't set the value if it is None
        if value is None:
            return

        # Set the data for the task_attribute.
        self.data[instance] = value

    def resolve(self, instance, value):
        """ Uses the resolver from the Task instance to resolve any replacements
        found in the value, and then converts it to the correct type.
        """

        # Get the resolver from the Task instance
        resolver = instance.resolver

        # Resolve any replacements in the value
        value = resolver.resolve(value)

        # If there are options, make sure the value is one of them.
        if self.attribute_options is not None:
            if value not in self.attribute_options:
                # Need to make some extra effort to be certain that it is not actually there...
                passed = False
                for option in self.attribute_options:
                    try:
                        # Attempt to convert to the type of the option, then check value.
                        converted_value = self.convert_to_type(value, type(option))
                        if converted_value == option:
                            passed = True
                            value = converted_value
                            break
                    except ValueError:
                        pass
                if not passed:
                    raise ValueError("Invalid value '%s' received. Expected one of %s" % (value, self.attribute_options))

        # Check to make sure that the value is the correct type
        if self.attribute_type is not None:
            # Need to make some extra effort to be certain that it does not match...
            value = self.convert_to_type(value, self.attribute_type)

        # And finally, we return the value. Let the calling function decide whether 
        # or not to set the resolved value back on the TaskAttribute.
        return value

    @classmethod
    def convert_to_type(cls, value, attribute_type):
        """ Utility function to attempt to convert an object to a specific type.

            Note: Only tested to work with the standard python types.

            Args:
                value (object): A python object to attempt to convert to type
                attribute_type (Type): A type to try and convert to.

            Returns:
                Object converted to the desired type.
            
            Raises:
                TypeError: If unable to convert to the specified type.
        """
        if isinstance(value, attribute_type):
            # Already the correct type.
            pass
        elif (isinstance(value, basestring) and 
            not issubclass(attribute_type, basestring)):
            try:
                # Attempt to convert the value to the correct type.
                converted_value = ast.literal_eval(value)
                if type(converted_value) == attribute_type:
                    value = converted_value
            except SyntaxError:
                raise TypeError("Invalid type received. '%s' received, and could not be parsed to: %s" % (value, attribute_type))
            except ValueError:
                raise ValueError("Value '%s' could not be parsed." % value)
        else:
            # Literal eval does not work on string based classes so do a regular cast conversion for strings.
            try:
                # Attempt to convert the value to the correct type.
                value = attribute_type(value)
            except TypeError:
                raise TypeError("Invalid type '%s' received. Expected '%s'" % (type(value), attribute_type))

        return value

class TaskType(type):

    def __new__(meta, name, bases, dct):
        classObj = super(TaskType, meta).__new__(meta, name, bases, dct)
        
        # Store all the TaskAttribute descriptors in an ordered dictionary so that 
        # we can access them later in the workflow designer. They need to be kept 
        # in order because the workflow designer should display the TaskAttributes 
        # in the order that they are added to the class.
        # Note: Turns out that this is a wrong assumption. Values do not appear in __dict__ in the same order that they are added to the class. (I Think this is a python 2.7 vs 3.x difference).
        classObj.task_attributes = collections.OrderedDict()
        for cl in reversed(classObj.__mro__[:-1]):
            for name, attr in list(cl.__dict__.items()):
                if isinstance(attr, TaskAttribute):
                    classObj.task_attributes[name] = attr

        # Register all tasks to the wolfkrow.core.tasks module.
        from wolfkrow.core.tasks import all_tasks
        if classObj.__name__ != "Task":
            all_tasks[classObj.__name__] = classObj

        return classObj


class Task(with_metaclass(TaskType, object)):
    """ Base Object used for every task. The TaskGraph will be used to build 
        graph of tasks from configuration, which will later be executed as a 
        series of tasks to complete a job.

        Includes the following methods to be overridden by children:
            validate *Optional* - This method should validate that the Task 
                Object was created correctly
            
            setup *Required* - This method should perform any setup required 
                for the task to run successfully.
            
            run *Required* - This method should do the bulk of the work


        The order of operations on a task is as follows:
        Locally:
            Validate -- Runs immediately after export is called.
        Farm:
            Setup -- Called immediately after the task object is executed.
            Run -- Called immediately after the Setup method is called.
    """

    name = TaskAttribute(default_value=None, configurable=True, attribute_type=str)
    name_prefix = TaskAttribute(default_value=None, configurable=False, attribute_type=str)
    dependencies = TaskAttribute(default_value=[], configurable=False, attribute_type=list, serialize=False)
    external_dependencies = TaskAttribute(default_value="", configurable=False, attribute_type=str, serialize=False,
        description="""Comma separated list of dependency ID's that are not part of the task graph. These are the ID's of existing tasks which must be completed before this task can start. Currently only relevant for Deadline submission.""")
    replacements = TaskAttribute(default_value={}, configurable=False, attribute_type=dict)
    resolver_search_paths = TaskAttribute(default_value=[], configurable=False, attribute_type=list)
    path_swap_lookup = TaskAttribute(default_value={}, configurable=False, auto_resolve=False, attribute_type=dict)
    config_files = TaskAttribute(
        default_value=[],
        configurable=False,
        attribute_type=list,
        description="""List of config files used to reconstruct the Loader object on the farm."""
    )

    temp_dir = TaskAttribute(default_value=None, configurable=False, attribute_type=str)

    python_script_executable = TaskAttribute(default_value=None, configurable=True, attribute_type=str, serialize=False)
    python_script_executable_args = TaskAttribute(default_value=None, configurable=True, attribute_type=list, serialize=False)
    command_line_executable = TaskAttribute(default_value=None, configurable=True, attribute_type=str, serialize=False)
    command_line_executable_args = TaskAttribute(default_value=None, configurable=True, attribute_type=list, serialize=False)
    sgtk = TaskAttribute(default_value=None, configurable=False, serialize=False)

    def __init__(self, **kwargs):
        """ Initializes Task object

            Accepts all kwargs, then checks if there is a corresponding TaskAttribute, then will set the value.

            Kwargs:
                name (str): Name of the task. Must be unique as it is used as an id in the TaskGraph.
                dependencies list[str]: List of other task names that this task depends on
                replacements: dict{str: str}: A dictionary of values that will be used by the task object later on.
        """
        # Create a copy of the replacements. Every task should be responsible for 
        # it's own replacements after creation.
        replacements = kwargs.get("replacements", {})
        kwargs["replacements"] = replacements.copy()

        # And use the resolved kwargs to set the task attributes.
        for arg in kwargs:
            attribute = self.task_attributes.get(arg)
            if attribute is not None:
                self.__setattr__(arg, kwargs[arg])

        # Build the resolver for future use. Every task should get it's own, and
        # each tasks resolver is responsible for resolving any replacements used
        # within the task.
        self.resolver = Resolver(
            self.replacements, 
            self.resolver_search_paths, 
            self.path_swap_lookup, 
            sgtk=self.sgtk
        )

        if self.python_script_executable is None:
            self.python_script_executable = os.environ.get("WOLFKROW_DEFAULT_PYTHON_SCRIPT_EXECUTABLE")

        if self.python_script_executable_args is None:
            self.python_script_executable_args = os.environ.get("WOLFKROW_DEFAULT_PYTHON_SCRIPT_EXECUTABLE_ARGS")

        if self.command_line_executable is None:
            self.command_line_executable = os.environ.get("WOLFKROW_DEFAULT_COMMAND_LINE_EXECUTABLE")
        
        if self.command_line_executable_args is None:
            items = os.environ.get("WOLFKROW_DEFAULT_COMMAND_LINE_EXECUTABLE_ARGS", "").split(",")
            self.command_line_executable_args = items

    @property
    def full_name(self):
        """ Returns the name of the task. """
        if not self.name_prefix:
            return self.name

        return self.name_prefix + "_" + self.name

    def add_dependency(self, task_name):
        # We need to get the dependencies without resolving them. This is because 
        # the resolver only returns a copy of the resolved value, so when we update
        # the dependency next, we will only be updating the copy.
        dependencies = Task.dependencies.__get__(self, dont_resolve=True)

        dependencies.append(task_name)

    def copy(self):
        """ Creates a copy of itself.

            Note: We cannot use copy.copy because the default implementation of 
                __copy__ does not copy the value found in each descriptor for the 
                copied object (Which makes sense if you think about it).
        """
        other = copy.copy(self)
        for task_attribute in self.task_attributes:
            setattr(other, task_attribute, getattr(self, task_attribute))

        return other

    def __call__(self):
        """ Validates, sets up, then runs this Task Object.

            Returns:
                True: If successfully completed
                False: If unsuccessfully completed

            Raises:
                TaskValidationException: Invalid task configuration.
        """

        self.setup()
        try: 
            return self.run()
        except Exception as e:
            traceback.print_exc()
            logging.error("Run method for task '%s' Failed. Reason: %s" % (self.name, e))
            return 1

    def validate(self):
        """ Method for Validating that this task Object was properly created. 
            Will raise an exception if validation fails

            Validation happens as the first step of the export process.
        """
        pass

    def setup(self):
        """ Abstract method for doing initial tasks required for the run method to 
            complete successfully. Will raise an exception if unable to properly 
            set-up the task.
        """

        raise NotImplementedError("setup method must be overridden by child class")

    def run(self):
        """ Abstract method for the work that should be done by this Task Object.

            Returns:
                True: If successfully completed
                False: If unsuccessfully completed
        """

        raise NotImplementedError("run method must be overridden by child class")

    def _get_script_path(self, extension, job_name=None, temp_dir=None):
        """ Helper method for generating a script name for script export methods.

        Args:
            job_name (str): Human readable token to be used as part of the file name.
            extension (str): The extension of the filepath to create.
        
        Kwargs:
            temp_dir (str):  temp directory to generate the script path to.
        """

        def sub_space_for_underscore(string):
            return string.strip().replace(" ", "_")

        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if job_name:
            script_name = "{time}_{job_name}_{task_name}.{extension}".format(
                time=now,
                job_name=sub_space_for_underscore(job_name),
                task_name=sub_space_for_underscore(self.full_name),
                extension=extension,
            )
        else:
            script_name = "{time}_{task_name}.{extension}".format(
                time=now,
                task_name=sub_space_for_underscore(self.full_name),
                extension=extension,
            )


        if self.temp_dir is None:
            self.temp_dir = temp_dir

        temp_dir = temp_dir or self.temp_dir

        file_path = os.path.join(temp_dir, script_name)

        return file_path

    def _command_line_sanitize_attribute(
        self, attribute_name, attribute_value, deadline=False
    ):
        """
        Processes the attribute value to prepare it for use on the command line.

        Default implementation just returns the given value.
        """
        return attribute_value

    def export_to_command_line(self, job_name=None, temp_dir=None, deadline=False, export_json=True):
        """
        Generates a `wolfkrow_run_task` command line command to run in order to
        re-construct and run this task via command line.

        Args:
            job_name (str): The name of the job that this task is a part of.
                Only used to generate the script's name.
            temp_dir (str): Temp directory to write a BASH script to
            deadline (bool): Whether to prepare this task for Deadline.
        """
        if self.command_line_executable is None:
            raise TaskException(
                "WOLFKROW_DEFAULT_COMMAND_LINE_EXECUTABLE variable undefined "
                "and no executable specified."
            )

        if not self.temp_dir:
            self.temp_dir = temp_dir

        task_args_dict = {}

        for attribute_name, attribute_obj in list(self.task_attributes.items()):
            if attribute_obj.serialize is False:
                continue

            value = attribute_obj.__get__(self)
            if value is None or value == attribute_obj.default_value:
                continue

            sanitised_value = self._command_line_sanitize_attribute(
                attribute_name, value, deadline=deadline
            )

            task_args_dict[attribute_name] = sanitised_value

        task_args = []

        if export_json:
            # If the executable is Wolfkrow, then write all the args to a JSON
            # file and pass the path in as a single arg
            json_file_path = self._get_script_path(
                extension="json", job_name=job_name, temp_dir=temp_dir
            )

            try:
                with open(json_file_path, "w") as json_file:
                    json.dump(task_args_dict, json_file, ensure_ascii=False, indent=4)

            except Exception as exception:
                raise TaskException(
                    "Couldn't write args JSON file to path: %s - %s"
                    % (json_file_path, exception)
                )

            start_frame = task_args_dict.get("start_frame")
            end_frame = task_args_dict.get("end_frame")

            # Include the start + end frames, as we want Deadline to be able to
            # replace them for chunked jobs
            if start_frame not in (None, "None"):
                task_args.append("--start_frame \"%s\"" % start_frame)
            if end_frame not in (None, "None"):
                task_args.append("--end_frame \"%s\"" % end_frame)

            task_args.append("--json_args_file \"%s\"" % json_file_path)

        else:
            # For other executables, pass the args in as "--key value" pairs
            for attribute_name, attribute_value in task_args_dict.items():
                task_args.append(
                    "--{attribute_name} {value}".format(
                        attribute_name=attribute_name,
                        value=attribute_value
                    )
                )

        # Now put together the arg string
        arg_str = "--task_name {task_name} ".format(task_name=self.__class__.__name__)
        arg_str += " ".join(task_args)
        
        exported_task = TaskExport(
            self, 
            executable=self.command_line_executable, 
            executable_args=self.command_line_executable_args,
            args=arg_str
        )

        return [exported_task]

    def _generate_bash_script_contents(self, job_name, temp_dir=None, deadline=False):
        """
        Generates the contents for a bash script export. Default implementation
        is just based on the CommandLine export.

        Args:
            job_name (str): The name of the job that this task is a part of.
                Only used to generate the script's name.

        Kwargs:
            temp_dir (str): temp directory to use for the command line export.
            deadline (bool): whether or not to prepare this task for Deadline.
        """
        command_line_export = self.export_to_command_line(
            job_name=job_name, temp_dir=temp_dir, deadline=deadline
        )

        bash_scripts = []
        bash_script_template = textwrap.dedent(
            """
            #!/usr/bin/env bash

            {command}
            """
        ).strip()

        for task, bash_command in command_line_export:
            bash_script = bash_script_template.format(command=bash_command)
            bash_scripts.append((task, bash_script))

        return bash_scripts

    def export_to_bash_script(self, job_name, temp_dir=None, deadline=False):
        """ Uses the standard export to command line method, then writes that to 
        a bash script.

        Args:
            job_name (str): name of the job this task is a part of. Only used in generation of the scripts name.

        Kwargs:
            temp_dir (str): temp directory to write the stand alone python script to.
            deadline (bool): whether or not to prepare this task for deadline.
        """

        bash_scripts = self._generate_bash_script_contents(job_name, deadline=deadline)

        bash_script_exports = []

        for task, bash_script in bash_scripts:
            bash_script_path = task._get_script_path(
                extension="sh", 
                job_name=job_name,
                temp_dir=temp_dir
            )

            with open(bash_script_path, 'w') as handle:
                handle.write(bash_script)

            # Ensure that the script is readonly for the person exporting. This 
            # is due to a security vulnerability due to some Task types containing 
            # sensitive data. Such as the SG tasks which may contain api keys or
            # auth tokens.
            # We also want to prevent write access to prevent someone modifying 
            # the script between creation and execution.
            # TODO: ensure this also works on Windows.
            os.chmod(bash_script_path, 0o500) # Sets "r-x------" permissions

            bash_script_exports.append((task, bash_script_path))

        return bash_script_exports

    def export_to_python_script(self, job_name, temp_dir=None, deadline=False):
        """ Will Export this task into a stand alone python script in order to run this task later. 
            
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

        if self.python_script_executable is None:
            raise TaskException("WOLFKROW_DEFAULT_PYTHON_SCRIPT_EXECUTABLE variable undefined and no executable specified.")

        file_path = self._get_script_path(
            extension="py",
            job_name=job_name,
            temp_dir=temp_dir
        )

        obj_str = repr(self)
        contents = """
import sys
from {module} import {obj_type}
callable = {obj_str}
ret = callable()
sys.exit(ret)""".format(
            module=self.__class__.__module__,
            obj_type=self.__class__.__name__,
            obj_str=obj_str
        )

        with open(file_path, 'w') as handle:
            handle.write(contents)

        # Ensure that the script is readonly for the person exporting. This 
        # is due to a security vulnerability due to some Task types containing 
        # sensitive data. Such as the SG tasks which may contain api keys or
        # auth tokens.
        # We also want to prevent write access to prevent someone modifying 
        # the script between creation and execution.
        # TODO: ensure this also works on Windows.
        os.chmod(file_path, 0o500) # Sets "r-x------" permissions

        return [(self, file_path)]

    def export(self, export_type="Json", temp_dir=None, job_name=None, deadline=False):
        """ Will Export this task in order to run later. This is to allow for 
            synchronous execution of many tasks among many machines. Intended 
            to be used alongside a distributed render manager (Something like 
            Tractor2, or deadline).

            Args:
                export_type (str): *Deprecated* Should be "Json". All other export methods are deprecated.
            
            Kwargs:
                temp_dir (str): Passed onto the PythonScript export method. 
                    Used to choose where to write the python script to.
                job_name (str): Passed onto the PythonScript export method. 
                    Used to choose the name of the exported python script.

            returns:
                (self, created_obj) - created_obj will either be a command line string to run OR the file path to a python script.
        """

        self.validate()

        # Assign the temp_dir variable so that the tempdir is available after submission.
        if self.temp_dir is None:
            self.temp_dir = temp_dir

        # Also add the temp_dir to our replacements if we don't already have one.
        if "temp_dir" not in self.replacements:
            self.update_replacements({"temp_dir": self.temp_dir})

        # Now we have the final temp dir. Lets make sure it exists:
        try:
            if not os.path.exists(self.temp_dir):
                os.makedirs(self.temp_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        exported_tasks = []

        # Export the sub tasks
        # Note: The sub_tasks are exported first incase exporting the subtasks 
        # changes any attributes in the parent task.
        sub_tasks = self.export_subtasks(
            export_type, 
            temp_dir=self.temp_dir, 
            job_name=job_name, 
            deadline=deadline
        )

        # Export the parent task.
        if export_type == "CommandLine":
            exported_tasks.extend(
                self.export_to_command_line(job_name, temp_dir=self.temp_dir, deadline=deadline, export_json=False)
            )
        elif export_type == "Json":
            exported_tasks.extend(
                self.export_to_command_line(job_name, temp_dir=self.temp_dir, deadline=deadline, export_json=True)
            )
        elif export_type == "BashScript":
            exported_tasks.extend(self.export_to_bash_script(job_name, temp_dir=self.temp_dir, deadline=deadline))
        elif export_type == "PythonScript":
            exported_tasks.extend(self.export_to_python_script(job_name, temp_dir=self.temp_dir, deadline=deadline))
        elif export_type == "Json":
            exported_tasks.extend(
                self.export_to_command_line(job_name, temp_dir=self.temp_dir, deadline=deadline, export_json=True)
            )
        else:
            raise TaskException("Unknown export type: {}. Expected one of 'CommandLine', 'BashScript', or 'PythonScript'".format(
                export_type
            ))

        # Add the sub tasks to the exported tasks list.
        exported_tasks.extend(sub_tasks)
        return exported_tasks

    def export_subtasks(self, export_type, temp_dir=None, job_name=None, deadline=False):
        all_exported_subtasks = []
        subtasks = self.get_subtasks()

        #TODO: If job_name is passed in, we need to modify it for each subtask so 
        #   that each job still has a unique name.

        for subtask in subtasks:
            exported_subtasks = subtask.export(
                export_type,
                temp_dir=temp_dir,
                #job_name=job_name,
                deadline=deadline
            )
            all_exported_subtasks.extend(exported_subtasks)

        return all_exported_subtasks

    def get_subtasks(self):
        """ Gives each Task object the opportunity add additional tasks to the task_graph 
            before submission.

            Default implemention returns an empty list.
        """

        return []

    def update_replacements(self, new_replacements):
        """ Updates the replacements dictionary with the new_replacements dictionary. 

            Args:
                new_replacements (dict): The dictionary of replacements to update with.
        """

        # We need to get the replacements without resolving them. This is because 
        # the resolver only returns a copy of the resolved value, so when we update
        # the replacements next, we will only be updating the copy.
        replacements = Task.replacements.__get__(self, dont_resolve=True)

        replacements.update(new_replacements)

        # Tell the resolver that our replacements have changed, so that it can re-resolve the replacements.
        self.resolver.refresh_replacements()

    def __repr__(self):
        """ Official string representation of self.

                Note: Will only work properly if all task_attributes values have 
                __repr__ defined to correctly re-create the object from a str.
        """

        # We only want to serialize the 'TaskAttribute' attributes which are all 
        # defined at the class level as descriptors. to get all instances, we m
        argStr = ""
        for attribute_name, attribute_obj  in list(self.task_attributes.items()):
            if attribute_obj.serialize:
                argStr = argStr + attribute_name + "=" + repr(attribute_obj.__get__(self)) + ", "
        argStr = argStr.rstrip(", ")


        rep = self.__class__.__name__ + "(" + argStr + ")"
        return str(rep)

    @classmethod
    def from_dict(
        cls, 
        data_dict, 
        replacements=None, 
        resolver_search_paths=None, 
        path_swap_lookup=None,
        config_files=None, 
        sgtk=None, 
        temp_dir=None
    ):
        """ Generic implementation of the 'from_dict' method for converting a dictionary
            containing the data for a Task object into a Task object. For more control
            over the conversion process, please override this method on your custom 
            Task's.

            Note: The default implementation will assume the keys in the data dictionary 
                correspond directly to an attribute on the Task object being constructed

            Args:
                data_dict (dict): Dictionary containing the data to construct the Task object.
            
            Kwargs:
                replacements (dict): A dictionary of string replacements.
                config_files (list): List of file paths used as the configuration 
                    files which constructed this task.
                sgtk (SGTK): SGTK configuration instance. Useful if your pipeline is integrated 
                    with sgtk.
        """

        # Ensure that temp_dir is added so that the task can be configured with 
        # a {temp_dir} replacement
        if temp_dir and "temp_dir" not in replacements:
            replacements["temp_dir"] = temp_dir

        # Do not add NoneType values to the dictionary, so we can use the default TaskAttribute values instead.
        filtered_data_dict = {}
        for key, value in list(data_dict.items()):
            if value is not None:
                filtered_data_dict[key] = value

        filtered_data_dict["config_files"] = config_files

        if "replacements" not in filtered_data_dict:
            filtered_data_dict["replacements"] = replacements

        if "resolver_search_paths" not in filtered_data_dict:
            filtered_data_dict["resolver_search_paths"] = resolver_search_paths

        if "path_swap_lookup" not in filtered_data_dict:
            filtered_data_dict["path_swap_lookup"] = path_swap_lookup

        if temp_dir and "temp_dir" not in filtered_data_dict:
            filtered_data_dict["temp_dir"] = temp_dir

        # If we have a sgtk instance, then add it to the task Object. We don't 
        # know what some custom task definitions might want it for.
        if sgtk:
            if sgtk in filtered_data_dict:
                print("Warning: 'sgtk' in Task data but being overwritten by a SGTK project configuration instance")
            filtered_data_dict["sgtk"] = sgtk

        obj = cls(**filtered_data_dict)
        return obj
        
