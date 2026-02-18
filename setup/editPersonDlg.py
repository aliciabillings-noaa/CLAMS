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
import messagedlg

class editPersonDlg(QDialog, ui_EditPersonnelDlg.Ui_EditPersonnelDlg):

    changed = pyqtSignal()

    def __init__(self, db, parent=None):
        super(editPersonDlg, self).__init__(parent)
        self.setupUi(self)
        self.mode = 'Add'

        self.db = db
        self.schema = parent.schema
        self.errorSounds=parent.errorSounds
        self.errorIcons=parent.errorIcons

        #  set up signals
        self.editPersonBtn.clicked.connect(self.editPersonClicked)
        self.cancelBtn.clicked.connect(self.cancelClicked)

        # setup reoccuring dlgs
        self.message = messagedlg.MessageDlg(self)

    # Populate fields, if creating a new record then fields will be blank
    # otherwise populate fields with existing user edited
    def setUp(self, currPerson):
        if (currPerson and len(currPerson) > 0):
            self.scientistLabel.setText(currPerson[0])
            self.affiliationLabel.setText(currPerson[1])
            self.isActive.setChecked(True if currPerson[2] == 'Yes' else False)
            self.editPersonBtn.setText('Update Personnel')
            self.mode = 'Edit'
        else:
            self.scientistLabel.setText('')
            self.affiliationLabel.setText('')
            self.isActive.setChecked(False)
            self.editPersonBtn.setText('Add Personnel')
            self.mode = 'Add'
    
    def editPersonClicked(self):
        scientist = self.scientistLabel.text()
        affiliation = self.affiliationLabel.text()
        isActive = 1 if self.isActive.isChecked() else 0
        sql = ''

        # If fields are pre-filled, we are updating a record
        if (self.mode == 'Edit'):
            if (not scientist or scientist == ''):
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                            "Empty Scientist field! Please complete before updating.", 'info')
                self.message.exec()
                return

            if (not affiliation or affiliation == ''):
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                            "Empty Affiliation field! Please complete before upating.", 'info')
                self.message.exec()
                return
            
            sql = ("UPDATE " + self.schema + ".personnel SET active=" + str(isActive) +
                   " WHERE scientist='" + scientist + "' and affiliation='" + affiliation + "'")
        # Otherwise, create new record
        elif (self.mode == 'Add'):
            sql = ("INSERT INTO " + self.schema + ".personnel (scientist, affiliation, active)"
            " VALUES ('"+ scientist + "', '" + affiliation + "', '" + str(isActive) + "')")

        self.db.dbExec(sql)

        #  emit the changed signal to update parent
        self.changed.emit()

        self.close()
    
    def cancelClicked(self):
        self.close()


