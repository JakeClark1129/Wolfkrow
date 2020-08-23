""" Module implementing a nuke render task.

	Author: Jacob-c
"""

import errno
import os
import shutil

from .task import Task, TaskAttribute
from .task_exceptions import TaskValidationException

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
		""" Initialize the FileCopy Object

			Args:
				source (str): Source file for FileCopy Task
				destination (str): Destination file for FileCopy Task
		"""
		super(FileCopy, self).__init__(**kwargs)

	def validate(self):
		""" Preforms Validation checks for FileCopy Task. Will ensure the source and destination files have been specified, and that the source
			file exists.

			Raises:
				TaskValidationException: FileCopy task is not properly initialized
		"""

		if self.source == "" or self.source is None:
			raise TaskValidationException("FileCopy task has no source")

		if self.destination == "" or self.destination is None:
			raise TaskValidationException("FileCopy task has no destination")

	def setup(self):
		""" Will create destination directory if it does not already exist.

			Raises: 
				OSError: Unable to create destination directory
		"""

		if self.destination.endswith(os.sep) or os.path.isdir(self.destination):
			directory = self.destination
		else:
			directory = os.path.dirname(self.destination)

		if not os.path.exists(directory):
			try:
				os.makedirs(directory)
			except OSError as e:
				if e.errno != errno.EEXIST:
					raise


	def run(self):
		""" Performs file copy.
		"""

		shutil.copy2(self.source, self.destination)
		return True