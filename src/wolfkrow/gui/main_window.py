import sys

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtGui import QPainter, QBrush, QPen
from PyQt5.QtCore import Qt, QPoint

from workflowDesigner.taskSelectorWidget import TaskSelector
from workflowDesigner.taskWidget import TaskWidget
from workflowDesigner.utils.connectorLine import ConnectorLine
from tasks import all_tasks



class main(QtWidgets.QMainWindow):
	def __init__(self):
		super(main, self).__init__()
		uic.loadUi('python/workflowDesigner/UI/mainWindow.ui', self)
		self.show()

		self.populateUI()

		self.setAcceptDrops(True)
		self.previousPos = None
		self.draggingLineObj = None

		self.lines = []
		cl = ConnectorLine(self)
		cl.inPos = QPoint(50, 100)
		cl.outPos = QPoint(150, 150)
		self.lines.append(cl)

	def populateUI(self):
		#self.populateTaskList()
		self.taskSelector = TaskSelector(self)
		self.taskSelector.move(self.width() - self.taskSelector.width(), 0)
		self.taskSelector.show()
		#self.taskSelector.

	def populateTaskList(self):
		for i in range(0, 5):

			
			label = QtWidgets.QPushButton("item%d" % i)
			label.show()
			self.taskListLayout.addWidget(label)
	
	def paintEvent(self, event):
		painter = QPainter(self)
		painter.setPen(QPen(Qt.black, 2, Qt.SolidLine))
		
		for line in self.lines:
			painter.drawLine(line.inPos.x(), line.inPos.y(), line.outPos.x(), line.outPos.y())

	def mousePressEvent(self, event):
		
		for line in self.lines:
			if line.isClicked(event.pos(), 50):
				print ("Is clicked %s" % line.inPos)
				self.clickedSide = line.getClickedSide(event.pos())
				self.draggingLineObj = line
				self.draggingLineStartPos = event.pos()

	def mouseMoveEvent(self, event):
		if event.buttons() == Qt.LeftButton:
			if self.draggingLineObj is not None and self.clickedSide in ["inPos", "outPos"]:
				distance = event.pos() - self.draggingLineStartPos
				if distance.manhattanLength() > 5:
					self.draggingLineObj.__setattr__(self.clickedSide, event.pos())
					self.repaint()

		super(main, self).mouseMoveEvent(event)
	
	def mouseReleaseEvent(self, event):
		self.clickedSide = None
		self.draggingLineObj = None
		self.draggingLineStartPos = None
	
	def dragEnterEvent(self, e):
		print ("DRAGGING ENTERED MAIN WINDOW")
		if e.mimeData().hasFormat('text/plain'):
			print("DRAGGING ACCEPTED")
			e.accept()
		else:
			print("DRAGGING IGNORED")
			e.ignore()

	def dropEvent(self, e):
		print ("DROP EVENT INITIATED")
		text = e.mimeData().text()
		print ("TEXT: %s" % text)
		if text.startswith("TaskClass:"):
			taskName = text.split(":")[1:]
			
			#Join on ':' incase the task name itself has a colon.
			taskName = ":".join(taskName)
			print ("taskName: %s" % taskName)
			
			taskClass = None
			for task_name in all_tasks:
				print("TaskClass: %s" % task_name)
				if taskName == task_name:
					taskClass = all_tasks[task_name]
					break

			#TODO: If taskClass is found, then initialize a new taskWidget.
			if taskClass is not None:
				newWidget = TaskWidget(taskClass, self)
				newWidget.move(e.pos().x(), e.pos().y())
				newWidget.show()

		print ("DROP EVENT DONE")

if __name__ == '__main__':
	import os

	app = QtWidgets.QApplication(sys.argv)
	window = main()
	app.exec_()

	sys.exit(0)





