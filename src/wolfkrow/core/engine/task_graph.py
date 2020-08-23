""" taskGraph Module for building a task graph and executing it as a job.

	Author: Jacob Clark
"""

import logging
import networkx
import subprocess
import tempfile

logging.basicConfig(level=logging.WARNING)

class TaskGraphException(Exception):
	""" Exception for generic TaskGraph errors
	"""
	pass

class TaskGraphValidationException(TaskGraphException):
	""" Exception for TaskGraph validation errors
	"""
	pass


class TaskGraph(object):
	""" Provides an interface to build, and execute a series of tasks.
	"""

	def __init__(self, name, replacements=None):
		""" Initializes TaskGraph object.

			Args: 
				name (str): The name of the task graph. This is purely cosmetic and has no impact on task graph execution.
			
			Kwargs:
				replacements (dict): A dictionary of string replacements used by tasks.
		"""
		self._graph = networkx.DiGraph()
		self._tasks = {}
		self.name = name
		self.replacements = replacements or {}

	def add_task(self, task):
		""" Adds a task to the task dictionary, and to the graph network.

			Note: When adding a task to the task graph, we will also add all the tasks dependencies to the graph regardless of whether or not
			the Task Object exists.

			Args:
				task (Task): Task Object to add.

			Raises:
				TaskGraphException: Task Name in Graph is not Unique.
		"""

		if self._tasks.get(task.name) is None:
			self._tasks[task.name] = task
		else:
			raise TaskGraphException("Task Name is not Unique: %s." % task.name)

		self._graph.add_node(task.name)

		# Edges are added such that when the task graph is built it goes from "depended on task => dependent task". This results in the most 
		# depended on tasks being at the top of the tree when sorting Topologically. which will result in the correct order of task execution
		edges = [(dependency, task.name) for dependency in task.dependencies]
		self._graph.add_edges_from(edges)

	def validate_task_graph(self):
		""" Validates the current Task graph.

			Raises:
				TaskGraphValidationException: Invalid Task Graph
		"""

		if not networkx.is_directed_acyclic_graph(self._graph):
			raise TaskGraphValidationException("Task Graph contains circular dependencies.")

	def export_tasks(self):
		""" Exports each individual task to its standalone state for execution.
		"""

		exported_tasks = {}

		tempdir = tempfile.mkdtemp()
		print("TEMPDIR: " + tempdir)

		for task_name, task in self._tasks.items():

			script = task.export(tempdir, self.name)

			exported_tasks[task_name] = {
				"executable": task.executable,
				"script": script,
				"obj": task,
			}

		return exported_tasks

	def execute_local(self):

		exported_tasks = self.export_tasks()

		results = {}
		taskExecutionOrder = networkx.topological_sort(self._graph)
		for taskName in taskExecutionOrder:
			task = exported_tasks.get(taskName)
			if task is None:
				logging.debug("Skipping Task '%s' because it was added as a dependency, but was never added to the TaskGraph." % taskName)
				continue

			ready = True
			for dependencyName in task['obj'].dependencies:
				# If the dependency has no entry, it means it was never actually added it to the task graph.
				if results.get(dependencyName) is False:
					ready = False
					break

			if not ready:
				logging.warning("This task's dependencies failed to execute. Skipping task: '%s'" % task.name)
				continue

			command = "{executable} {script}".format(
				executable=task['executable'], 
				script=task['script']
			)

			# shell=true is a security liability in this case since the exported 
			# scripts can be modified before execution begin.
			process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
			stdout, stderr = process.communicate()
			if process.returncode == 0:
				logging.info("Task '%s' Successfully completed" % task['obj'].name)
				results[task['obj'].name] = True
			else:
				logging.error("Task '%s' Failed. Will skip all dependant tasks." % task['obj'].name)
				results[task['obj'].name] = False

		#TODO: Cleanup the tempdir from exported_tasks.

	def execute_legacy(self):
		""" Executes the task graph.

			Note: Executes tasks in Topological order based on their dependencies. 
				This means the order of execution may vary for tasks not dependent 
				on one another.

			Note: This is a simple implementation of execute which results in asynchronous
				task execution on a single machine. Ideally there would be an implementation
				that will export each task, then dispatch the tasks to a render 
				farm for synchronous task execution where possible.

			Note: Marked as legacy because it naively assumes all tasks are capable 
				of being run in the same environment. Some tasks will require unique 
				execution environments. Such as a nuke render task might require 
				nuke to be importable. (Therefore needs to be run with "nuke -t ..."
				instead of "python ...")
		"""

		self.validate_task_graph()
		
		results = {}
		taskExecutionOrder = networkx.topological_sort(self._graph)
		for taskName in taskExecutionOrder:
			task = self._tasks.get(taskName)
			# Due to how we handle dependencies it is possible that we have tasks in our task graph that never actually existed.
			if task is None:
				logging.debug("Skipping Task '%s' because it was added as a dependency, but was never added to the TaskGraph." % taskName)
				continue
			
			logging.info("Running task: %s" % taskName)

			#Determine if this task's dependencies have successfully completed. Otherwise skip it
			ready = True
			for dependencyName in task.dependencies:
				# If the dependency has no entry, it means it was never actually added it to the task graph.
				if results.get(dependencyName) is False:
					ready = False
					break
			
			if not ready:
				logging.warning("This task's dependencies failed to execute. Skipping task: '%s'" % task.name)
				continue

			#Run the task
			result = task()
			results[task.name] = result
			if result is False:
				logging.error("Task '%s' Failed. Will skip all dependant tasks." % task.name)
			else:
				logging.info("Task '%s' Successfully completed" % task.name)

