
import os
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
    def __init__(self, config_file_paths=None, replacements=None):
        if config_file_paths is None:
            config_file_paths = os.environ.get('WOLFKROW_CONFIG_SEARCH_PATHS')
            if config_file_paths:
                config_file_paths = config_file_paths.split(",")

        if config_file_paths is None:
            raise LoaderException("Configuration file not specified and 'WOLFKROW_CONFIG_SEARCH_PATHS' not set.")
        self._config_file_paths = config_file_paths
        self.__config = None
        self.replacements = replacements or {}
        # Ensure that the replacements dictionary is an instance of ReplacementsDict
        if not isinstance(self.replacements, utils.ReplacementsDict):
            self.replacements = utils.ReplacementsDict(self.replacements)

    @property
    def config(self):
        if self.__config is None:
            self.__config = self._load_configs(self._config_file_paths)
        
        return self.__config

    def _load_configs(self, config_file_paths):
        config = {}
        for config_file in config_file_paths:
            with open(config_file, "r") as handle:
                file_contents = handle.read()

            config_snippet = yaml.load(file_contents, Loader=yaml.
            FullLoader)
            config.update(config_snippet)

        # replace replacements
        for replacement in config['replacements']:
            # Should configured replacements overwrite replacements that are passed 
            # into the tool, or viceversa?
            self.replacements.update(replacement)

        def replace_replacements_dict_crawler(dictionary, replacements):
            for key, value in dictionary.items():
                if isinstance(value, dict):
                    replace_replacements_dict_crawler(value, replacements)
                elif isinstance(value, list):
                    for index in range(len(value)):
                        if isinstance(value[index], dict):
                            replace_replacements_dict_crawler(value[index], replacements)
                        elif isinstance(value[index], str):
                            value[index] = string.Formatter().vformat(value[index], (), replacements)
                elif isinstance(value, str):
                    dictionary[key] = string.Formatter().vformat(value, (), replacements)

        replace_replacements_dict_crawler(config, self.replacements)

        return config

    def parse_workflow(self, workflow_name):

        task_graph = TaskGraph("workflow", replacements=self.replacements)
        workflow_tasks = None
        for workflow in self.config['workflows']:
            if workflow_name in workflow.keys():
                workflow_tasks = workflow[workflow_name]
                break
        
        if workflow_tasks is None:
            raise Exception("Unable to find workflow '{}'".format(workflow_name))

        tasks_lookup = {}
        for task in self.config['tasks']:
            for task_name in task.keys():
                tasks_lookup[task_name] = task[task_name]

        #TODO: Add extra validation for the config file. (ensure tasks requested 
        # in the workflow section are defined in the tasks section)
        for task_name in workflow_tasks:

            task_data_dict = tasks_lookup.get(task_name)

            task_obj = tasks.all_tasks.get(task_data_dict['task_type'])
            if task_obj is None:
                continue
                #TODO: Warn about missing task definition but still continue without the task.
            
            task_data_dict['name'] = task_name
            task = task_obj.from_dict(task_data_dict)
            task_graph.add_task(task)

        task_graph.execute_local()


if __name__ == "__main__":
    loader = Loader([r"C:\Projects\Wolfkrow\src\wolfkrow\builder\config_file.yaml"])
    loader.parse_workflow("Convert to Tiff")