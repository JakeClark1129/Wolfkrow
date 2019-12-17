import logging
import collections

from weakref import WeakKeyDictionary


class TaskAttribute(object):
	""" A Descriptor Class intended for use with Task Objects. Using these descriptor objects allows us to store metadata about each attribute 
		on a Task, such as what the type should be, and whether or not it should show up as a configurable attribute on the workflow designer.
	"""

	def __init__(self, defaultValue=None, configurable=False, attributeType=None):
		""" Initialize the TaskAttribute object.
		
			Kwargs:
				defaultValue: The default value of the attribute
				configurable (bool): Whether or not this attribute should show up as a configurable attribute in the workflow designer.
		"""

		# Must be a WeakKeyDictionary to allow garbage collection to clean up our tasks when we are done with them. (Not that this matters because 
		# this program will typically be short lived, and the memory used by TaskAttributes will be minimal. Also, Tasks will typically live 
		# for the entire duration of the program)

		# WARNING: Using the WeakKeyDictionary opens us up to some very hard to debug issues. If garbage collection cleans up one of our TaskAttribute
		# objects, it will also get removed from this dictionary. If this happens while we are iterating through the dictionary, then weird stuff 
		# can happen. (Meaning don't iterate through this dictionary!)
		self.data = WeakKeyDictionary()

		self.defaultValue = defaultValue
		self.configurable = configurable
		self.attributeType = attributeType

	def __get__(self, instance, instance_type=None):
		""" Getter function. Will return the stored value for the specified instance if it exists, otherwise it will return the defaultValue
		"""

		if instance is not None:
			return self.data.get(instance, self.defaultValue)
		else:
			# If we get this attribute from the class level, then we return the descriptor object instead of an object level value, This allows
			# us to easily get a reference to the descriptor object. (Which allows us to access the metadata about this attribute easily)
			return self

	def __set__(self, instance, value):
		""" Setter function. Will set the given value in the data dictionary using the instance as the key in the dictionary.
			
			Note: This method will first check that the type of the value matches the type that this TaskAttribute instance is expecting
		"""

		if self.attributeType is not None and value is not None and not isinstance(value, self.attributeType):
			raise TypeError("Invalid type %r received. Expected %s" % (type(value), self.attributeType))

		self.data[instance] = value


class TaskType(type):

	def __new__(meta, name, bases, dct):
		classObj = super().__new__(meta, name, bases, dct)
		
		# Store all the TaskAttribute descriptors in an ordered dictionary so that we can access them later in the workflow designer. They need
		# to be kept in order because the workflow designer should display the TaskAttributes in the order that they are added to the class.
		classObj.taskAttributes = collections.OrderedDict()
		for cl in reversed(classObj.__mro__[:-1]):
			for name, attr in cl.__dict__.items():
				if isinstance(attr, TaskAttribute):
					classObj.taskAttributes[name] = attr

		return classObj

class Task(metaclass=TaskType):
	""" Base Object used for every task. The TaskGraph will be used to build graph of tasks from configuration, which will later be executed 
		as a series of tasks to complete a job.

		Includes the following Abstract methods which must be overridden by children:
			validate(self) - This method should validate that the Task Object was created correctly
			setup(self) - This method should perform any setup tasks required for the primary run method to complete successfully.
			run(self) - This method should do the bulk of the work
	"""

	name = TaskAttribute(defaultValue=None, configurable=True, attributeType=str)
	dependencies = TaskAttribute(defaultValue=[], configurable=False, attributeType=list)
	replacements = TaskAttribute(defaultValue={}, configurable=False, attributeType=dict)

	def __init__(self, **kwargs):
		""" Initializes Task object

			Accepts all kwargs, then checks if there is a corresponding TaskAttribute, then will set the value.

			Kwargs:
				name (str): Name of the task. Must be unique as it is used as an id in the TaskGraph.
				dependencies list[str]: List of other task names that this task depends on
				replacements: dict{str: str}: A dictionary of values that will be used by the task object later on.
		"""

		for arg in kwargs:
			attribute = self.taskAttributes.get(arg)
			if attribute is not None:
				self.__setattr__(arg, kwargs[arg])

	def __call__(self):
		""" Validates, sets up, then runs this Task Object.

			Returns:
				True: If successfully completed
				False: If unsuccessfully completed

			Raises:
				TaskValidationException: Invalid task configuration.
		"""

		self.validate()
		self.setup()
		try: 
			return self.run()
		except Exception as e:
			logging.error("Run method for task '%s' Failed. Reason: %s" % (self.name, e))
			return False

	def validate(self):
		""" Abstract method for Validating that this task Object was properly created. Will raise an exception if validation fails
		"""
		
		raise NotImplementedError("validate method must be overridden by child class")

	def setup(self):
		""" Abstract method for doing initial tasks required for the run method to complete successfully. Will raise an exception if unable 
			to properly set-up the task.
		"""

		raise NotImplementedError("setup method must be overridden by child class")

	def run(self):
		""" Abstract method for the work that should be done by this Task Object.

			Returns:
				True: If successfully completed
				False: If unsuccessfully completed
		"""

		raise NotImplementedError("run method must be overridden by child class")

	def export(self):
		""" Will Export this task into a stand alone state to assist with allowing synchronous execution of tasks among many machines. This 
			function is intended to be used alongside a distributed render manager (Something like Pixar's Tractor2)
			
			TODO: Create a fairly generic implementation that takes advantage of __repr__ on each task, then does some logic to determine 
			imports required, then writes a .py file that can be executed on its own to execute this task
		"""

		raise NotImplementedError("Export method Not Implemented.")
		
	def __repr__(self):
		""" Official string representation of self.

				Note: Will only work properly if all instance variables have __repr__ defined to match this format.
		"""

		argStr = ""
		for attribute in self.__dict__:
			value = getattr(self, attribute)

			argStr = argStr + attribute + "=" + repr(value) + ", "
		argStr = argStr.rstrip(", ")

		rep = self.__class__.__name__ + "(" + argStr + ")"
		return str(rep)