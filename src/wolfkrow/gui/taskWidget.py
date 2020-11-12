import inspect

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import Qt

from tasks.task import Task, TaskAttribute
from workflowDesigner.taskAttributeWidget import TaskAttributeWidget

class TaskWidget(QtWidgets.QWidget):

    def __init__(self, taskType, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi('python/workflowDesigner/UI/taskWidget.ui', self)

        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor(200, 200, 200))

        self.setAutoFillBackground(True)
        self.setPalette(pal)

        self.setAcceptDrops(True)
        self.taskType = taskType
        self.setupUI()

        self.dependencies = []
        self.dependants = []

    def setupUI(self):
        if not issubclass(self.taskType, Task):
            raise Exception("Invalid taskType assigned to task Widget. %s" % self.taskType)


        self.setMinimumSize(QtCore.QSize(40, 0))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        self.setSizePolicy(sizePolicy)

        self.userInputWidgets = {}
        totalHeightOfUserInputs = 30
        self.Name.setText(self.taskType.__name__)
        for name, attribute in self.taskType.task_attributes.items():
            if not attribute.configurable:
                continue
                
            taskAttributeWidget = TaskAttributeWidget(name, attribute, self)
            totalHeightOfUserInputs += taskAttributeWidget.height()
            taskAttributeWidget.move(0, totalHeightOfUserInputs)
            self.userInputWidgets[name] = taskAttributeWidget

        self.resize(self.width(), self.height() + totalHeightOfUserInputs)

    def drawConnector(self):
        pass

    def paintEvent(self, event):
        pass

    def mousePressEvent(self, event):
        self.__mousePressPos = None
        self.__mouseMovePos = None
        if event.button() == Qt.LeftButton:
            self.__mousePressPos = event.globalPos()
            self.__mouseMovePos = event.globalPos()

        super(TaskWidget, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            # adjust offset from clicked point to origin of widget
            currPos = self.mapToGlobal(self.pos())
            globalPos = event.globalPos()
            diff = globalPos - self.__mouseMovePos
            newPos = self.mapFromGlobal(currPos + diff)
            self.move(newPos)

            self.__mouseMovePos = globalPos

        super(TaskWidget, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.__mousePressPos is not None:
            moved = event.globalPos() - self.__mousePressPos 
            if moved.manhattanLength() > 3:
                event.ignore()
                return

        super(TaskWidget, self).mouseReleaseEvent(event)



    def dragEnterEvent(self, e):
        print("DRAGGING ENTERED on movable label")
        e.accept()

    def dropEvent(self, e):
        print("Dropper")
