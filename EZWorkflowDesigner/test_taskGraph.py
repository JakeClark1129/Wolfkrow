import logging
logging.basicConfig(level=logging.DEBUG)
import taskGraph
from FileCopy import FileCopy

class TestTask_Successful(taskGraph.Task):
	def __init__(self, **kwargs):
		super(TestTask_Successful, self).__init__(**kwargs)

	def validate(self):
		return True

	def setup(self):
		return True

	def run(self):
		return True


class TestTask_Failed_Validate(taskGraph.Task):
	def __init__(self, **kwargs):
		super(TestTask_Failed_Validate, self).__init__(**kwargs)

	def validate(self):
		raise taskGraph.TaskValidationException("Task is rigged to fail")

	def setup(self):
		return True

	def run(self):
		return True


class TestTask_Failed_Run(taskGraph.Task):
	def __init__(self, **kwargs):
		super(TestTask_Failed_Run, self).__init__(**kwargs)

	def validate(self):
		return True

	def setup(self):
		return True

	def run(self):
		#logging.info("'%s' was unsuccessfully run because it is rigged to fail" % self.name)
		raise taskGraph.TaskGraphException("Rigged to fail")
		return False


def test_taskGraphExecuteSuccess():
	logging.info("===========================================")
	logging.info("RUNNING TEST 'test_taskGraphExecuteSuccess'")
	logging.info("===========================================")
	job = taskGraph.TaskGraph()
	t1 = TestTask_Successful(name="Task1", dependencies=[], replacements={})
	t2 = TestTask_Successful(name="Task2", dependencies=["Task1"], replacements={})
	t3 = TestTask_Successful(name="Task3", dependencies=["Task2", "Task1"], replacements={})
	t4 = TestTask_Successful(name="Task4", dependencies=["Task3"], replacements={})
	t5 = TestTask_Successful(name="Task5", dependencies=[], replacements={})

	job.addTask(t1)
	job.addTask(t2)
	job.addTask(t3)
	job.addTask(t4)
	job.addTask(t5)
	
	try: 
		job.execute()
		error = False
	except Exception:
		error = True
	finally:
		if not error:
			logging.info("TEST 'test_taskGraphExecuteFailed_validation' SUCCESSFUL")
		else:
			logging.info("TEST 'test_taskGraphExecuteFailed_validation' FAILED")

def test_taskGraphExecuteFailed_validation():
	logging.info("=====================================================")
	logging.info("RUNNING TEST 'test_taskGraphExecuteFailed_validation'")
	logging.info("=====================================================")
	job = taskGraph.TaskGraph()
	t1 = TestTask_Successful(name="Task1", dependencies=[], replacements={})
	t2 = TestTask_Successful(name="Task2", dependencies=["Task1"], replacements={})
	t3 = TestTask_Failed_Validate(name="Task3", dependencies=["Task2", "Task1"], replacements={})
	t4 = TestTask_Successful(name="Task4", dependencies=["Task3"], replacements={})
	t5 = TestTask_Successful(name="Task5", dependencies=[], replacements={})

	job.addTask(t1)
	job.addTask(t2)
	job.addTask(t3)
	job.addTask(t4)
	job.addTask(t5)

	try: 
		job.execute()
		error = False
	except Exception:
		error = True
	finally:
		if error:
			logging.info("TEST 'test_taskGraphExecuteFailed_validation' SUCCESSFUL")
		else:
			logging.info("TEST 'test_taskGraphExecuteFailed_validation' FAILED")
		

	

def test_taskGraphExecuteFailed_run():
	logging.info("==============================================")
	logging.info("RUNNING TEST 'test_taskGraphExecuteFailed_run'")
	logging.info("==============================================")
	job = taskGraph.TaskGraph()
	t1 = TestTask_Successful(name="Task1", dependencies=[], replacements={})
	t2 = TestTask_Successful(name="Task2", dependencies=["Task1"], replacements={})
	t3 = TestTask_Failed_Run(name="Task3", dependencies=["Task2", "Task1"], replacements={})
	t4 = TestTask_Successful(name="Task4", dependencies=["Task3"], replacements={})
	t5 = TestTask_Successful(name="Task5", dependencies=[], replacements={})

	job.addTask(t1)
	job.addTask(t2)
	job.addTask(t3)
	job.addTask(t4)
	job.addTask(t5)

	try: 
		job.execute()
		error = False
	except Exception:
		error = True
	finally:
		if not error:
			logging.info("TEST 'test_taskGraphExecuteFailed_validation' SUCCESSFUL")
		else:
			logging.info("TEST 'test_taskGraphExecuteFailed_validation' FAILED")



test_taskGraphExecuteSuccess()
test_taskGraphExecuteFailed_validation()
test_taskGraphExecuteFailed_run()



fc = FileCopy(name="Create BackUp", source="C:/Projects/MyPythonScripts/wolfkrow/taskGraph.py", destination="C:/backups/")
fc()
print fc