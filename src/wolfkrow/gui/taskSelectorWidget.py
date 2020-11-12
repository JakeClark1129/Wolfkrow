from PyQt5 import QtCore, QtGui, QtWidgets, uic
from tasks import all_tasks

from workflowDesigner.taskSelectorItemWidget import TaskSelectorItem

class TaskSelector(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super(TaskSelector, self).__init__(*args, **kwargs)
        uic.loadUi('python/workflowDesigner/UI/taskSelector.ui', self)
        self.taskObj = TaskSelectorItem
        self.tasks = []
        self.populate()
        self.format()

    def format(self):
        posY = 0
        for task in self.tasks:
            task.move(0, posY)
            posY = posY + task.geometry().height() + 10

    def populate(self):
        """ Iterates through all tasks in all_tasks and creates a TaskSelectorItem object as a child of this object.
        """
        
        counter = 0
        for task_name in all_tasks:
            taskObj = self.taskObj(task_name, all_tasks[task_name], self)
            self.tasks.append(taskObj)
            self.tasks[counter].show()
            counter+=1
        