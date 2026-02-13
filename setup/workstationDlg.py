# coding=utf-8

#     National Oceanic and Atmospheric Administration (NOAA)
#     Alaskan Fisheries Science Center (AFSC)
#     Resource Assessment and Conservation Engineering (RACE)
#     Midwater Assessment and Conservation Engineering (MACE)

#  THIS SOFTWARE AND ITS DOCUMENTATION ARE CONSIDERED TO BE IN THE PUBLIC DOMAIN
#  AND THUS ARE AVAILABLE FOR UNRESTRICTED PUBLIC USE. THEY ARE FURNISHED "AS
#  IS."  THE AUTHORS, THE UNITED STATES GOVERNMENT, ITS INSTRUMENTALITIES,
#  OFFICERS, EMPLOYEES, AND AGENTS MAKE NO WARRANTY, EXPRESS OR IMPLIED,
#  AS TO THE USEFULNESS OF THE SOFTWARE AND DOCUMENTATION FOR ANY PURPOSE.
#  THEY ASSUME NO RESPONSIBILITY (1) FOR THE USE OF THE SOFTWARE AND
#  DOCUMENTATION; OR (2) TO PROVIDE TECHNICAL SUPPORT TO USERS.

"""
.. module:: workstationnDlg

    :synopsis: Shows all workstation records from the workstation table

| Developed by:  Melina Shak <melina.shak@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS
|
| Author:
|       Melina Shak <melina.shak@noaa.gov>
| Maintained by:
|       Melina Shak <melina.shak@noaa.gov>
"""

#  imports
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from ui import ui_WorkstationDlg
import setup.editWorkstationDlg as editWorkstationDlg

class workstationDlg(QDialog, ui_WorkstationDlg.Ui_WorkstationDlg):

    def __init__(self, db, parent=None):
        super(workstationDlg, self).__init__(parent)
        self.setupUi(self)

        self.db = db
        self.schema = parent.schema
        self.errorSounds=parent.errorSounds
        self.errorIcons=parent.errorIcons

        self.dialog = editWorkstationDlg.editWorkstationDlg(self.db, parent=self)

        #  set up signals
        self.addBtn.clicked.connect(self.addClicked)
        self.editBtn.clicked.connect(self.editClicked)
        self.doneBtn.clicked.connect(self.doneClicked)

        # populate workstation table from database
        self.populateWorkstation()
    
    def addClicked(self):
        """
          add a new workstation.
        """
        self.dialog.setUp([])
        self.dialog.exec()
        
    def editClicked(self):
        currentRow = self.workstationTable.currentRow()
        record = []

        record.append(self.workstationTable.item(currentRow, 0).text())
        
        self.dialog.setUp(record)
        self.dialog.exec()
        
    def populateWorkstation(self):
        self.workstationTable.clearContents()
        self.workstationTable.setRowCount(0)
        rowCount = 0

        sql = ("SELECT workstation_id, hostname, description from workstations order by workstation_id")
        query = self.db.dbQuery(sql)

        for id, hostname, description in query:
            self.workstationTable.insertRow(rowCount)
            self.workstationTable.setItem(rowCount, 0, QTableWidgetItem(id))
            self.workstationTable.setItem(rowCount, 1, QTableWidgetItem(hostname))
            self.workstationTable.setItem(rowCount, 2, QTableWidgetItem(description))
            rowCount += 1

        #  resize columns and scroll to bottom
        self.workstationTable.resizeColumnsToContents()
        self.workstationTable.scrollToBottom()

    def doneClicked(self):
        self.reject()
