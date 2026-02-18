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
import messagedlg

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
        self.editBtn.clicked.connect(self.editClicked)
        self.cancelBtn.clicked.connect(self.cancelClicked)

        # setup reoccuring dlgs
        self.message = messagedlg.MessageDlg(self)

        self.action_map = {
            'Trawl Event': self.trawlAction,
            'Enter Catch': self.catchAction,
            'Administration': self.adminAction,
            'Utilities': self.utilitiesAction
        }

        self.module_map = {
            'Haul': self.haulModule,
            'Specimen': self.specimenModule,
            'CatchSWFSC': self.catchSWFSCModule
        }

    # Populate fields, if creating a new record then fields will be blank
    # otherwise populate fields with existing user edited
    def setUp(self, workstation):
        if (workstation and len(workstation) > 0):
            sql = ("SELECT w.workstation_id, w.hostname, w.status, w.description, w.active, " +
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
            id, hostname, status, description, isActive, mainActions, modules = query.first()

            self.idLabel.setText(id)
            self.hostnameLabel.setText(hostname)
            self.statusCB.setCurrentIndex(0 if status == 'closed' else 1)
            self.descriptionLabel.setText(description)
            self.isActive.setChecked(True if isActive == '1' else False)
            self.editBtn.setText('Edit Workstation')

            if mainActions:
                self.sync_checkboxes(mainActions, self.action_map)

            if modules:
                self.sync_checkboxes(modules, self.module_map)
        else:
            # set id for new workstation: get maxId and increment
            sql = 'SELECT MAX(workstation_id) from workstations'
            query = self.db.dbQuery(sql)
            id, = query.first()
            newId = int(id) + 1
            self.idLabel.setText(str(newId))

            self.hostnameLabel.setText('')
            self.statusCB.setCurrentIndex(0)
            self.descriptionLabel.setText('')
            self.isActive.setChecked(False)
            self.editBtn.setText('Add Workstation')

            self.sync_checkboxes("", self.action_map)
            self.sync_checkboxes("", self.module_map)
    
    def editClicked(self):
        status = self.statusCB.currentText()
        hostName = self.hostnameLabel.text()
        description = self.descriptionLabel.text()
        id = self.idLabel.text()
        active = "1" if self.isActive.isChecked() else "0"

        # Ensure fields listed below are not blank, if so display error message
        fields_to_validate = [
            ("hostname", hostName),
            ("description", description)
        ]
        for name, value in fields_to_validate:
            if not value or not value.strip():
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                            f"Empty {name} field! Please complete before updating.", 'info')
                self.message.exec()
                
        mainActionStr = self.createStringFromCheckboxes(self.action_map)
        moduleStr = self.createStringFromCheckboxes(self.module_map)
                    
        if self.editBtn.text() == 'Edit Workstation': 
            # Update workstation row
            preparedQuery = self.db.prepare("UPDATE " + self.schema + ".WORKSTATIONS SET "
                f"hostname=:hostname, status=:status, description=:description, active=:active WHERE workstation_id=:id")
            data = {
                ':hostname': hostName, 
                ':status': status, 
                ':description': description, 
                ':active': active, 
                ':id': id}
            self.db.dbExecPrepared(preparedQuery, data)

            # Update mainActions and modules rows in workstation_configuration 
            sql = ("UPDATE " + self.schema + ".WORKSTATION_CONFIGURATION SET "
                f"parameter_value='{mainActionStr}' WHERE workstation_id={id} and parameter='MainActions'")
            self.db.dbExec(sql)

            sql = ("UPDATE " + self.schema + ".WORKSTATION_CONFIGURATION SET "
                f"parameter_value='{moduleStr}' WHERE workstation_id={id} and parameter='Modules'")
            self.db.dbExec(sql)
        else:
            # Create new record in workstations table
            preparedQuery = self.db.prepare("INSERT INTO " + self.schema + ".WORKSTATIONS "
                "(workstation_id, hostname, status, description, active) VALUES "
                "(:id, :hostname, :status, :description, :active)")
            data = {
                ':id': id,
                ':hostname': hostName,
                ':status': status,
                ':description': description,
                ':active': active
            }
            self.db.dbExecPrepared(preparedQuery, data)

            # Create mainActions and modules row in workstation_configuration
            sql = "INSERT INTO " + self.schema + ".WORKSTATION_CONFIGURATION " \
                "(workstation_id, parameter, parameter_value) " \
                f"values ({id}, 'MainActions', '{mainActionStr}'), "  \
                f"({id}, 'Modules', '{moduleStr}')"
            self.db.dbExec(sql)
        
        #  emit the changed signal to update parent
        self.changed.emit()

        self.close()
    
    # From a string, determine which check boxes to show as checked or unchecked
    def sync_checkboxes(self, csv_string, widget_map):
    # Handle None or empty strings safely, and strip whitespace!
    # Using a set {} makes lookups faster and cleaner
        active_items = {x.strip() for x in (csv_string or "").split(',')}
    
        for key, widget in widget_map.items():
            # Set Checked to True if key exists, False if it doesn't
            widget.setChecked(key in active_items)
    
    # Create string based on check boxes
    def createStringFromCheckboxes(self, widget_map):
        vals = []
        for key, widget in widget_map.items():
            if (widget.isChecked()):
                vals.append(key)
        return ','.join(vals)

    def cancelClicked(self):
        self.close()


