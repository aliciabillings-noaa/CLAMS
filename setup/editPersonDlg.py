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
.. module:: editPersonDlg

    :synopsis: UI to edit personnel table in database, can 
        add and edit records

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
from ui import ui_EditPersonnelDlg

class editPersonDlg(QDialog, ui_EditPersonnelDlg.Ui_EditPersonnelDlg):

    def __init__(self, db, currPerson, parent=None):
        super(editPersonDlg, self).__init__(parent)
        self.setupUi(self)

        self.db = parent.db
        self.schema = parent.schema

        if (currPerson and len(currPerson) > 0):
            self.scientistLabel.setText(currPerson[0])
            self.affiliationLabel.setText(currPerson[1])
            self.isActive.setChecked(True if currPerson[2] == 'Yes' else False)

        #  set up signals
        self.addPersonBtn.clicked.connect(self.addPersonClicked)
        self.cancelBtn.clicked.connect(self.cancelClicked)
    
    def addPersonClicked(self):
        scientist = self.scientistLabel.text()
        affiliation = self.affiliationLabel.text()
        isActive = 1 if self.isActive.isChecked() else 0

        sql = ("INSERT INTO " + self.schema + ".personnel (scientist, affiliation, active)"
            " VALUES ('"+ scientist + "', '" + affiliation + "', '" + str(isActive) + "')")
        self.db.dbExec(sql)

        self.accept()
    
    def cancelClicked(self):
        self.reject()


