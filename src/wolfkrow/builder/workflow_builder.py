from builtins import object
import copy
import os
import re
import string
import yaml
from ..core import tasks
from ..core.engine.task_graph import TaskGraph
from ..core.engine import resolver

class LoaderException(Exception):
    """ Exception for generic Task errors
    """
    pass

class Loader(object):
    """ Responsible for loading the configuration files and 
        creating a task graph from a given workflow_name inside 
        present inside of the config file.

        Note: Duplicate entries found in more than 1 config file are overwritten by config files found later in the list

        Args:
            config_file_paths (list): List of file paths to parse for the configured 
                work_flows. If not specified, it deafaults to the "WOLFKROW_CONFIG_SEARCH_PATHS" 
                environment variable.
    """
    def __init__(self, config_file_paths=None, replacements=None, sgtk=None, temp_dir=None):
        if config_file_paths is None:
            config_file_paths = os.environ.get('WOLFKROW_CONFIG_SEARCH_PATHS')
            config_file_paths = os.path.expandvars(config_file_paths)
            if config_file_paths:
                config_file_paths = config_file_paths.split(",")

        if config_file_paths is None:
            raise LoaderException("Configuration file not specified and 'WOLFKROW_CONFIG_SEARCH_PATHS' not set.")

        self._config_file_paths = config_file_paths
        self.__config = None
        self.replacements = replacements or {}
        self._sgtk = sgtk
        self.temp_dir = temp_dir

        # Ensure that the replacements dictionary is an instance of ReplacementsDict.
        # This is because ReplacementsDict has special logic to handle missing values
        if not isinstance(self.replacements, resolver.ReplacementsDict):
            self.replacements = resolver.ReplacementsDict(self.replacements)

    @property
    def config(self):
        if self.__config is None:
            self.__config = self._load_configs(self._config_file_paths)
        
        return self.__config

    def _update_config(self, current_dict, new_dict):
        
        # # Generic solution:
        # for key, value in new_dict.items():
        #     if key in current_dict:
        #         if type(value) != type(current_dict[key]):
        #             current_dict[key] = value
        #         elif isinstance(dict, value):
        #             self._update_config(current_dict[key], value)
        #         elif isinstance(list, value) or isinstance(set, value):
        #             for item in value:
        #                 pass

        # Custom solution:
        # Top level of the config. IE: task_attribute_defaults, replacements, tasks
        workflow_dict = new_dict.get("workflows")
        if workflow_dict:
            if "workflows" not in current_dict:
                current_dict["workflows"] = workflow_dict
            else:
                current_dict["workflows"].update(workflow_dict)

        tasks_dict = new_dict.get("tasks")
        if tasks_dict:
            if "tasks" not in current_dict:
                current_dict["tasks"] = tasks_dict
            else:
                current_dict["tasks"].update(tasks_dict)

        replacements_dict = new_dict.get("replacements")
        if replacements_dict:
            if "replacements" not in current_dict:
                current_dict["replacements"] = replacements_dict
            else:
                current_dict["replacements"].update(replacements_dict)

        resolver_search_paths = new_dict.get("resolver_search_paths")
        if resolver_search_paths:
            # resolver search paths completely override any previously specified search paths.
            current_dict["resolver_search_paths"] = resolver_search_paths

        task_attribute_defaults = new_dict.get("task_attribute_defaults")
        if task_attribute_defaults:
            if "task_attribute_defaults" not in current_dict:
                current_dict["task_attribute_defaults"] = task_attribute_defaults
            else:
                current_dict["task_attribute_defaults"].update(task_attribute_defaults)

        executables = new_dict.get("executables")
        if executables:
            if "executables" not in current_dict:
                current_dict["executables"] = executables
            else:
                current_dict["executables"].update(executables)

    def _load_configs(self, config_file_paths):
        config = {}
        for config_file in config_file_paths:

            # Check that the config file exists before loading it.
            if not os.path.exists(config_file):
                print("Warning: Wolfkrow config file {} was not found.".format(config_file))
                continue

            with open(config_file, "r") as handle:
                file_contents = handle.read()

            config_snippet = yaml.load(file_contents, Loader=yaml.Loader)
            self._update_config(config, config_snippet)

        # replace replacements
        # TODO: Should configured replacements overwrite replacements that are passed 
        # into the tool, or viceversa?
        self.replacements.update(config.get('replacements', {}))

        return config

    def tasks_from_task_names_list(self, task_names):
        """ Parses list of task names, to find in the configuration files. Then 
            constructs the corresponding list of tasks.

            Note: Task names not found in the configuration file will be ignored.

            Args: 
                task_names (list): List containing the names of tasks to look up 
                    in the configuration file.
            Returns:
                List: List of constructed tasks.
        """

        tasks_lookup = self.config['tasks']

        tasks_list = []
        for task_name in task_names:

            configured_task_data = tasks_lookup.get(task_name)
            if configured_task_data is None:
                continue

            default_task_data = self.get_default_task_data(configured_task_data['task_type'])
            task_data = copy.deepcopy(default_task_data)
            task_data.update(configured_task_data)

            task_type = task_data['task_type']
            task_obj = tasks.all_tasks.get(task_type)
            if task_obj is None:
                print("Warning: Task type '{task_type}' is undefined. Ignoring...".format(task_type=task_type))

            task_data['name'] = task_name
            task_data['config'] = self.config
            task = task_obj.from_dict(
                task_data, 
                replacements=self.replacements,
                resolver_search_paths=self.config.get("resolver_search_paths", []),
                config_files=self._config_file_paths, 
                temp_dir=self.temp_dir,
                sgtk=self._sgtk
            )
            tasks_list.append(task)

        return tasks_list

    def get_default_task_data(self, task_name):
        if task_name in self.config.get('task_attribute_defaults', []):
            return self.config['task_attribute_defaults'][task_name]
        return {}

    def get_task_data(self, task_name):
        # Get default task data dictionary
        configured_task_data = self.config['tasks'].get(task_name)
        if not configured_task_data:
            print("Warning: Task '{task_name}' is undefined. Ignoring...".format(task_name=task_name))
            return None

        default_task_data = self.get_default_task_data(configured_task_data['task_type'])
        task_data = copy.deepcopy(default_task_data)
        task_data.update(configured_task_data)

        return task_data

    def parse_workflow(self, workflow_name):

        task_graph = TaskGraph(
            workflow_name, 
            replacements=self.replacements, 
            temp_dir=self.temp_dir,
        )
        workflow_tasks = self.config['workflows'].get(workflow_name)

        if workflow_tasks is None:
            raise Exception("Unable to find workflow '{}'".format(workflow_name))

        for task_name in workflow_tasks:

            # Get default task data dictionary
            task_data = self.get_task_data(task_name)

            task_type = task_data['task_type']
            task_obj = tasks.all_tasks.get(task_type)
            if task_obj is None:
                print("Warning: Task type '{task_type}' is undefined. Ignoring...".format(task_type=task_type))
                continue

            task_data['name'] = task_name
            task_data['config'] = self.config
            task = task_obj.from_dict(
                task_data, 
                replacements=self.replacements, 
                resolver_search_paths=self.config.get("resolver_search_paths", []),
                config_files=self._config_file_paths, 
                temp_dir=self.temp_dir,
                sgtk=self._sgtk
            )
            task_graph.add_task(task)

        return task_graph

    def get_workflow_names(self):
        return self.config["workflows"].keys()


    def get_required_task_replacements(self, task_name):
        tasks_lookup = self.config["tasks"]

        task_data = self.get_task_data(task_name)
        if task_data is None:
            return None

        required_task_replacements = []

        for attribute, value in task_data.items():
            found_replacements = resolver.Resolver.check_for_replacements(value)
            if found_replacements:
                required_task_replacements.extend(found_replacements)

        return required_task_replacements


    def get_required_workflow_replacements(self, workflow_name):
        workflow = self.config["workflows"].get(workflow_name)

        if workflow is None:
            return None
        
        required_workflow_replacements = []

        for task_name in workflow:
            task_required_replacements = self.get_required_task_replacements(task_name)
            if task_required_replacements:
                required_workflow_replacements.extend(task_required_replacements)

        # Convert all the replacements to data objects
        # NOTE: This is a stop gap hack. We need to add configuration to the workflow definitions which allow techinical users to define required replacements.
        required_workflow_replacement_data_objects = []
        for replacement in required_workflow_replacements:
            replacement_data_object = RequiredReplacementData(replacement, options=None, strict=False)
            required_workflow_replacement_data_objects.append(replacement_data_object)

        return required_workflow_replacement_data_objects


class RequiredReplacementData():
    def __init__(self,replacement_name, default=None, options=None, strict=False):
        self.replacement_name = replacement_name
        self.default = default
        self.options = options
        self.strict = strict