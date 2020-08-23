
file_path = r"C:\Projects\Wolfkrow\src\wolfkrow\builder\config_file.yaml"


import ptvsd
ptvsd.enable_attach()
print ("Waiting for attach...")
ptvsd.wait_for_attach() 

import yaml
import wolfkrow.core.tasks as tasks
from wolfkrow.core.engine.task_graph import TaskGraph


class Loader(object):
	def __init__(self, config_file, replacements=None):
		self._config_file = config_file
		self.__config = None
		self.replacements = replacements or {}

	@property
	def config(self):
		if self.__config is None:
			self.__config = self._load_config(self._config_file)
		
		return self.__config

	def _load_config(self, config_file):
		with open(self._config_file, "r") as handle:
			file_contents = handle.read()
		config = yaml.load(file_contents, Loader=yaml.FullLoader)
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
			#Weird thing with python 3 -- You cannot do myDict.keys()[0]
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
	loader = Loader(r"C:\Projects\Wolfkrow\src\wolfkrow\builder\config_file.yaml")
	loader.parse_workflow("test_workflow")