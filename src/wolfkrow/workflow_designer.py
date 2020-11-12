import sys

from PyQt5 import QtCore, QtGui, QtWidgets, uic

from wolfkrow.gui import main_window


if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    window = main_window.main()
    
    app.exec_()

    sys.exit(0)