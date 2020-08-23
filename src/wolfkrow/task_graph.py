import sys

from tasks.fileCopy import FileCopy

if __name__ == '__main__':
	obj = FileCopy(source="abc", destination="def", dependencies=["OTHERS"], name="Copy Files")
	sys.exit(0)