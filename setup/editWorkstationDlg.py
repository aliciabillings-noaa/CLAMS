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
from ui import ui_EditWorkstationDlg

class editWorkstationDlg(QDialog, ui_EditWorkstationDlg.Ui_EditWorkstationDlg):

    changed = pyqtSignal()

    def __init__(self, db, parent=None):
        super(editWorkstationDlg, self).__init__(parent)
        self.setupUi(self)

        self.db = db
        self.schema = parent.schema
        self.errorSounds=parent.errorSounds
        self.errorIcons=parent.errorIcons

        #  set up signals
        self.cancelBtn.clicked.connect(self.cancelClicked)

    # Populate fields, if creating a new record then fields will be blank
    # otherwise populate fields with existing user edited
    def setUp(self, workstation):
        if (workstation and len(workstation) > 0):
            sql = ("SELECT w.workstation_id, w.hostname, w.status, w.description, w.active, w.current_event, " +
                   "wc_main.parameter_value AS main_actions, wc_mod.parameter_value AS modules " +
                   "FROM workstations w "
                   "LEFT JOIN workstation_configuration wc_main "
                   " ON w.workstation_id=wc_main.workstation_id  " +
                   "AND wc_main.parameter = 'MainActions' " +
                   "LEFT JOIN workstation_configuration wc_mod "
                   "ON w.workstation_id = wc_mod.workstation_id  " +
                   "AND wc_mod.parameter = 'Modules' "
                   "WHERE w.workstation_id = " + workstation[0])
            query = self.db.dbQuery(sql)
            id, hostname, status, description, isActive, currEvent, mainActions, modules = query.first()

            self.idLabel.setText(id)
            self.hostnameLabel.setText(hostname)
            self.statusLabel.setText(status)
            self.descriptionLabel.setText(description)
            self.isActive.setChecked(True if isActive == 1 else False)
            self.currLabel.setText(currEvent)
            self.mainActions.setText(mainActions)
            self.modules.setText(modules)
            self.editBtn.setText('Edit Workstation')
        else:
            self.idLabel.setText('')
            self.hostnameLabel.setText('')
            self.statusLabel.setText('')
            self.descriptionLabel.setText('')
            self.isActive.setChecked(False)
            self.currLabel.setText('')
            self.mainActions.setText('')
            self.modules.setText('')
            self.editBtn.setText('Add Workstation')
        
    def cancelClicked(self):
        self.close()


