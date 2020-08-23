""" Module implementing a nuke render task.
"""

import errno
import os
import shutil

from .task import Task, TaskAttribute
from .task_exceptions import TaskValidationException


#TODO: Implement NukeRender task.
class NukeRender(Task):
	""" NukeRender Task implementation. Will accept an nuke script, assumed to 
		have 1 read node, and 1 write node, then substitute the attributes on each.
	"""

	nuke_script = TaskAttribute(defaultValue="", configurable=True, attributeType=str)
	
	# Attributes for read node
	source = TaskAttribute(defaultValue="", configurable=True, attributeType=str)
	
	#attributes for write node
	destination = TaskAttribute(defaultValue="", configurable=True, attributeType=str)
	file_type = TaskAttribute(defaultValue="exr", configurable=True, attributeType=str)
	bit_depth = TaskAttribute(defaultValue="", configurable=True, attributeType=str)


	def __init__(self, **kwargs):
		""" Initialize the NukeRender Object

			Kwargs:
		"""
		super(NukeRender, self).__init__(**kwargs)

	def validate(self):
		""" Preforms Validation checks for NukeRender Task.

			Raises:
				TaskValidationException: NukeRender task is not properly initialized
		"""
		pass

	def setup(self):
		""" Will create destination directory if it does not already exist.

			Raises: 
				OSError: Unable to create destination directory
		"""
		pass

	def run(self):
		""" Performs file copy.
		"""
		pass