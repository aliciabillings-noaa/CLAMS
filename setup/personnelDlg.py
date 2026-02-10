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
.. module:: personnelDlg

    :synopsis: Shows all personnel records from the personnel table

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
from ui import ui_PersonnelDlg
import setup.editPersonDlg as editPersonDlg
import messagedlg

class personnelDlg(QDialog, ui_PersonnelDlg.Ui_PersonnelDlg):

    def __init__(self, db, parent=None):
        super(personnelDlg, self).__init__(parent)
        self.setupUi(self)

        self.db = db
        self.schema = parent.schema
        self.errorSounds=parent.errorSounds
        self.errorIcons=parent.errorIcons

        self.dialog = editPersonDlg.editPersonDlg(self.db, parent=self)

        #  set up signals
        self.addBtn.clicked.connect(self.addPersonClicked)
        self.editBtn.clicked.connect(self.editPersonClicked)
        self.doneBtn.clicked.connect(self.doneClicked)
        self.bulkEnableBtn.clicked.connect(self.bulkEnableClicked)
        self.bulkDisableBtn.clicked.connect(self.bulkDisableClicked)
        self.dialog.changed.connect(self.populatePersonnel)
        self.personnelTable.itemSelectionChanged.connect(self.updateButtonStatus)

        # populate personnel table from database
        self.populatePersonnel()
    
    def addPersonClicked(self):
        """
          add a new person.
        """
        self.dialog.setUp([])
        self.dialog.exec()
        
    def editPersonClicked(self):
        currentRow = self.personnelTable.currentRow()
        record = []

        record.append(self.personnelTable.item(currentRow, 0).text())
        record.append(self.personnelTable.item(currentRow, 1).text())
        record.append(self.personnelTable.item(currentRow, 2).text())
        
        self.dialog.setUp(record)
        self.dialog.exec()

    def updateButtonStatus(self):
        range = self.personnelTable.selectedRanges()
        currStatus = False

        if range:
            currStatus = True

        self.bulkEnableBtn.setEnabled(currStatus)
        self.bulkDisableBtn.setEnabled(currStatus)
    
    def bulkEnableClicked(self):
        self.bulkUpdate('1')
    
    def bulkDisableClicked(self):
        self.bulkUpdate('0')

    def bulkUpdate(self, activeStatus):
        range = self.personnelTable.selectedRanges()

        startIdx = range[0].topRow()
        endIdx = range[0].bottomRow()
        currIdx = startIdx            

        scientistsList = []
        while currIdx <= endIdx:
            currScientist = self.personnelTable.item(currIdx, 0).text()
            scientistsList.append(currScientist)
            currIdx += 1
        
        # 1. Format each item with quotes
        scientists = ["'{}'".format(item) for item in scientistsList]

        # 2. Join the quoted items with a comma and a space
        formattedSci = ", ".join(scientists)

        sql = ("UPDATE " + self.schema + ".personnel SET active=" + activeStatus +
                   " WHERE scientist in (" + formattedSci + ")")
        self.db.dbExec(sql)

        # refresh table
        self.populatePersonnel()
        
    def populatePersonnel(self):
        self.personnelTable.clearContents()
        self.personnelTable.setRowCount(0)
        rowCount = 0

        sql = ("SELECT scientist, affiliation, active from personnel order by scientist")
        query = self.db.dbQuery(sql)

        for scientist, affiliation, active in query:
            active = 'Yes' if active == '1' else 'No'
            self.personnelTable.insertRow(rowCount)
            self.personnelTable.setItem(rowCount, 0, QTableWidgetItem(scientist))
            self.personnelTable.setItem(rowCount, 1, QTableWidgetItem(affiliation))
            self.personnelTable.setItem(rowCount, 2, QTableWidgetItem(active))
            rowCount += 1

        #  resize columns and scroll to bottom
        self.personnelTable.resizeColumnsToContents()
        self.personnelTable.scrollToBottom()

    def doneClicked(self):
        self.reject()
