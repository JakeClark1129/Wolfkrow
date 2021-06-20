import collections
import copy
import datetime
import logging
import os
import six
import traceback

from weakref import WeakKeyDictionary

from wolfkrow.core.tasks.task_exceptions import TaskException
from wolfkrow.core import utils



class TaskAttribute(object):
    """ A Descriptor Class intended for use with Task Objects. Using these descriptor objects allows us to store metadata about each attribute 
        on a Task, such as what the type should be, and whether or not it should show up as a configurable attribute on the workflow designer.
    """

    def __init__(self, default_value=None, configurable=False, attribute_options=None, 
        attribute_type=None, required=False, serialize=True, description=None):
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

    def __get__(self, instance, instance_type=None):
        """ Getter function. Will return the stored value for the specified instance
            if it exists, otherwise it will return the default_value
        """

        if instance is not None:
            return self.data.get(instance, self.default_value)
        else:
            # If we get this attribute from the class level, then we return the 
            # descriptor object instead of an object level value, This allows us 
            # to easily get a reference to the descriptor object. (Which allows 
            # us to access the metadata about this attribute easily)
            return self

    def __set__(self, instance, value):
        """ Setter function. Will set the given value in the data dictionary using 
            the instance as the key in the dictionary.
            
            Note: This method will first check that the type of the value matches 
                the type that this TaskAttribute instance is expecting, or that 
                the value set is one of options.
        """

        if value is None:
            return

        if self.attribute_options is not None:
            if value not in self.attribute_options:
                raise TypeError("Invalid value %r received. Expected one of %s" % (value, self.attribute_options))
        if self.attribute_type is not None:
            if not isinstance(value, self.attribute_type):
                raise TypeError("Invalid type '%s' received. Expected %s" % (type(value), self.attribute_type))

        self.data[instance] = value

class TaskType(type):

    def __new__(meta, name, bases, dct):
        classObj = super(TaskType, meta).__new__(meta, name, bases, dct)
        
        # Store all the TaskAttribute descriptors in an ordered dictionary so that 
        # we can access them later in the workflow designer. They need to be kept 
        # in order because the workflow designer should display the TaskAttributes 
        # in the order that they are added to the class.
        classObj.task_attributes = collections.OrderedDict()
        for cl in reversed(classObj.__mro__[:-1]):
            for name, attr in cl.__dict__.items():
                if isinstance(attr, TaskAttribute):
                    classObj.task_attributes[name] = attr

        # Register all tasks to the wolfkrow.core.tasks module.
        from wolfkrow.core.tasks import all_tasks
        if classObj.__name__ != "Task":
            all_tasks[classObj.__name__] = classObj

        return classObj

@six.add_metaclass(TaskType)
class Task():
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
    dependencies = TaskAttribute(default_value=[], configurable=False, attribute_type=list, serialize=False)
    replacements = TaskAttribute(default_value={}, configurable=False, attribute_type=dict)
    config_files = TaskAttribute(
        default_value={}, 
        configurable=False, 
        attribute_type=list, 
        description="""List of config files used to reconstruct the Loader object 
on the farm."""
    )
    config = TaskAttribute(configurable=False, serialize=False)

    temp_dir = TaskAttribute(default_value=None, configurable=False, attribute_type=str)

    executable = TaskAttribute(default_value=None, configurable=True, attribute_type=str, serialize=False)
    executable_args = TaskAttribute(default_value=None, configurable=True, attribute_type=str, serialize=False)

    def __init__(self, **kwargs):
        """ Initializes Task object

            Accepts all kwargs, then checks if there is a corresponding TaskAttribute, then will set the value.

            Kwargs:
                name (str): Name of the task. Must be unique as it is used as an id in the TaskGraph.
                dependencies list[str]: List of other task names that this task depends on
                replacements: dict{str: str}: A dictionary of values that will be used by the task object later on.
        """

        for arg in kwargs:
            attribute = self.task_attributes.get(arg)
            if attribute is not None:
                self.__setattr__(arg, kwargs[arg])
        
        if self.executable is None:
            self.executable = os.environ.get("WOLFKROW_DEFAULT_TASK_EXECUTABLE")

        if self.executable_args is None:
            self.executable_args = os.environ.get("WOLFKROW_DEFAULT_TASK_EXECUTABLE_ARGS")

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
        if self.executable is None:
            raise TaskException("WOLFKROW_DEFAULT_TASK_EXECUTABLE variable undefined and no executable specified.")

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


    def export_to_command_line(self, temp_dir=None, deadline=False):
        """ Will generate a `wolfkrow_run_task` command line command to run in order to 
            re-construct and run this task via command line. 
        """

        if not self.temp_dir:
            self.temp_dir = temp_dir

        arg_str = ""
        for attribute_name, attribute_obj  in self.task_attributes.items():
            if attribute_obj.serialize:
                arg_str = "{arg_str} --{attribute_name} {value}".format(
                        arg_str=arg_str,
                        attribute_name=attribute_name,
                        value=repr(attribute_obj.__get__(self)
                    )
                )

        executable = self.config['executables'].get("wolfkrow_run_task", "wolfkrow_run_task.py")
        command = "{executable} --task_name {task_type} {task_args}".format(
            executable = executable,
            task_type=self.__class__.__name__, 
            task_args=arg_str
        )

        return (self, command)

    def export_to_python_script(self, job_name, temp_dir=None):
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

        def sub_space_for_underscore(string):
            return string.strip().replace(" ", "_")

        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        script_name = "{time}_{job_name}_{task_name}.py".format(
            time=now,
            job_name=sub_space_for_underscore(job_name),
            task_name=sub_space_for_underscore(self.name)
        )

        if self.temp_dir is None:
            self.temp_dir = temp_dir

        temp_dir = temp_dir or self.temp_dir

        file_path = os.path.join(temp_dir, script_name)

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
        return (self, file_path)

    def export(self, export_type, temp_dir=None, job_name=None, deadline=False):
        """ Will Export this task in order to run later. This is to allow for 
            synchronous execution of many tasks among many machines. Intended 
            to be used alongside a distributed render manager (Something like 
            Tractor2, or deadline).

            Args:
                export_type (str): One of "CommandLine" or "PythonScript". chooses which type of export is desired.
            
            Kwargs:
                temp_dir (str): Passed onto the PythonScript export method. 
                    Used to choose where to write the python script to.
                job_name (str): Passed onto the PythonScript export method. 
                    Used to choose the name of the exported python script.

            returns:
                (self, created_obj) - created_obj will either be a command line string to run OR the file path to a python script.
        """

        self.validate()

        if export_type == "CommandLine":
            return self.export_to_command_line(temp_dir=temp_dir, deadline=deadline)
        elif export_type == "PythonScript":
            return self.export_to_python_script(job_name, temp_dir=temp_dir)


    def __repr__(self):
        """ Official string representation of self.

                Note: Will only work properly if all task_attributes values have 
                __repr__ defined to correctly re-create the object from a str.
        """

        # We only want to serialize the 'TaskAttribute' attributes which are all 
        # defined at the class level as descriptors. to get all instances, we m
        argStr = ""
        for attribute_name, attribute_obj  in self.task_attributes.items():
            if attribute_obj.serialize:
                argStr = argStr + attribute_name + "=" + repr(attribute_obj.__get__(self)) + ", "
        argStr = argStr.rstrip(", ")


        rep = self.__class__.__name__ + "(" + argStr + ")"
        return str(rep)

    @classmethod
    def from_dict(cls, data_dict, replacements=None, config_files=None, temp_dir=None):
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
        """

        filtered_data_dict = {}
        # Do not add NoneType values to the dictionary, so we can use the default TaskAttribute values instead.
        if replacements:
            utils.replace_replacements_dict_crawler(data_dict, replacements)
        else:
            #TODO: Warn that there was no replacements passed into the function, so no replacements will be replaced successfully.
            pass

        for key, value in data_dict.items():
            if value is not None:
                filtered_data_dict[key] = value

        filtered_data_dict["config_files"] = config_files

        if temp_dir and "temp_dir" not in filtered_data_dict:
            filtered_data_dict["temp_dir"] = temp_dir

        obj = cls(**filtered_data_dict)
        return obj
        