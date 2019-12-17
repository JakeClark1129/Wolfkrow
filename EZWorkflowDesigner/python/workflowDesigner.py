import sys

from PyQt5 import QtCore, QtGui, QtWidgets, uic

from workflowDesigner import mainWindow


if __name__ == '__main__':

	app = QtWidgets.QApplication(sys.argv)
	window = mainWindow.main()
	
	app.exec_()

	sys.exit(0)


