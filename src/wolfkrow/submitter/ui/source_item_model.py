






import re
from collections import deque

from PySide2 import QtCore, QtGui


class SourceItemModel(QtCore.QAbstractTableModel):
    def __init__(self, source_items, workflows):
        super().__init__()

        # This is the list of source items in the order they were found on the 
        # file system
        self.source_items = source_items

        self.workflows = workflows

    def data(self, index, role):

        source_item = index.internalPointer()

        if role == QtCore.Qt.SourceItemRole:
            return source_item
        
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole or role == QtCore.Qt.ToolTipRole:
            # The first column is the workflow selection column
            if index.column() == 0:
                return self.workflows[source_item.selected_workflow]

            # -1 because the first column is the workflow selection column
            data = source_item.get_replacement_by_index(index.column() - 1)
            return data

        return None

    def setData(self, index, value, role):

        source_item = index.internalPointer()

        if role == QtCore.Qt.EditRole:

            if index.column() == 0:
                source_item.selected_workflow = int(value)
                return True

            # -1 because the first column is the checkbox column
            source_item.set_replacement_by_index(index.column() - 1, value)

            return True
        return False

    def hasIndex(self, row, column, parent):
        if parent.isValid():
            source_item = parent.internalPointer()
            if row >= len(source_item.children):
                return False
        else:
            if row < len(self.source_items):
                source_item = self.source_items[row]
            else: 
                return False
            
        if column > len(source_item.replacements) + 1:
            return False

        return True

    def index(self, row, column, parent):

        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        source_item = self.source_items[row]
        return self.createIndex(row, column, source_item)

    def columnCount(self, parent):
        if not self.source_items:
            return 0

        return len(self.source_items[0].replacements) + 1

    def rowCount(self, parent):
        return len(self.source_items)

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled

        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

        # The first column is always enabled.
        if index.column() == 0:
            flags |= QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled

        # Only enable the index if the source item is enabled
        source_item = index.internalPointer()
        if source_item.enabled == 2:
            flags |= QtCore.Qt.ItemIsEnabled

        return flags
    

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                if section == 0:
                    return "Workflow"

                section_name = list(self.source_items[0].replacements.keys())[section - 1]
                return section_name
            else:
                return section + 1
        return None