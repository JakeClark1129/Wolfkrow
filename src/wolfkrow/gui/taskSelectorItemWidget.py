from PyQt5 import QtCore, QtGui, QtWidgets, uic



class TaskSelectorItem(QtWidgets.QWidget):

	def __init__(self, name, taskType, *args, **kwargs):
		super(TaskSelectorItem, self).__init__(*args, **kwargs)
		uic.loadUi('python/workflowDesigner/UI/taskSelectorItemWidget.ui', self)

		self.name = name
		self.taskType = taskType
		self.Name.setText(name)

		self.initializeUI()

	def initializeUI(self):
		""" Initializes the UI attributes of this widget.
		"""

	def mouseMoveEvent(self, e):

		if e.buttons() != QtCore.Qt.LeftButton:
			return

		mimeData = QtCore.QMimeData()
		mimeData.setText("TaskClass:%s" % self.name)

		drag = QtGui.QDrag(self)
		drag.setMimeData(mimeData)
		drag.setHotSpot(e.pos() - self.rect().topLeft())

		dropAction = drag.exec_(QtCore.Qt.MoveAction)


	def mousePressEvent(self, e):
		super(TaskSelectorItem, self).mousePressEvent(e)
