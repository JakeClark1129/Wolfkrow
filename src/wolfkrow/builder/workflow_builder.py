import copy
import os
import re
import string
import yaml
import wolfkrow.core.tasks as tasks
from wolfkrow.core.engine.task_graph import TaskGraph
from wolfkrow.core import utils

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

        # Ensure that the replacements dictionary is an instance of ReplacementsDict
        if not isinstance(self.replacements, utils.ReplacementsDict):
            self.replacements = utils.ReplacementsDict(self.replacements)

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

            task_data = tasks_lookup.get(task_name)
            if task_data is None:
                continue

            task_obj = tasks.all_tasks.get(task_data['task_type'])
            if task_obj is None:
                #TODO: Warn about missing task definition but still continue without the task.
                continue

            task_data['name'] = task_name
            task_data['config'] = self.config
            task = task_obj.from_dict(
                task_data, 
                replacements=self.replacements, 
                config_files=self._config_file_path, 
                temp_dir=self.temp_dir,
            )
            tasks_list.append(task)

        return tasks_list

    def get_default_task_data(self, task_name):
        if task_name in self.config['task_attribute_defaults']:
            return self.config['task_attribute_defaults'][task_name]
        return {}

    def parse_workflow(self, workflow_name):

        task_graph = TaskGraph(
            workflow_name, 
            replacements=self.replacements, 
            temp_dir=self.temp_dir,
        )
        workflow_tasks = self.config['workflows'].get(workflow_name)
        
        if workflow_tasks is None:
            raise Exception("Unable to find workflow '{}'".format(workflow_name))

        #TODO: Add extra validation for the config file. (ensure tasks requested 
        # in the workflow section are defined in the tasks section)
        for task_name in workflow_tasks:

            # Get default task data dictionary
            configured_task_data = self.config['tasks'].get(task_name)
            if not configured_task_data:
                #TODO: Warn about missing task definition but still continue without the task.
                continue

            default_task_data = self.get_default_task_data(configured_task_data['task_type'])
            task_data = copy.deepcopy(default_task_data)
            task_data.update(configured_task_data)

            task_obj = tasks.all_tasks.get(configured_task_data['task_type'])
            if task_obj is None:
                #TODO: Warn about missing task definition but still continue without the task.
                continue
            
            task_data['name'] = task_name
            task_data['config'] = self.config
            task = task_obj.from_dict(
                task_data, 
                replacements=self.replacements, 
                config_files=self._config_file_paths, 
                temp_dir=self.temp_dir,
            )
            task_graph.add_task(task)

        return task_graph


if __name__ == "__main__":
    loader = Loader([r"C:\Projects\Wolfkrow\src\wolfkrow\builder\config_file.yaml"])
    loader.parse_workflow("Convert to Tiff")