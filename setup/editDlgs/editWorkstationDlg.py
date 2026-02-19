from ui import ui_EditWorkstationDlg
from .baseEditDlg import BaseEditDlg

class editWorkstationDlg(BaseEditDlg, ui_EditWorkstationDlg.Ui_EditWorkstationDlg):

    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.setupUi(self)

        # Wire the buttons
        self.setup_base()

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

    def setUp(self, workstation):
        # If we have an ID (workstation list has data), it's an Edit
        if workstation and len(workstation) > 0:
            # (Keeping your original complex query logic)
            sql = ("SELECT w.workstation_id, w.hostname, w.status, w.description, w.active, "
                   "wc_main.parameter_value, wc_mod.parameter_value "
                   "FROM workstations w "
                   "LEFT JOIN workstation_configuration wc_main ON w.workstation_id=wc_main.workstation_id "
                   "AND wc_main.parameter = 'MainActions' "
                   "LEFT JOIN workstation_configuration wc_mod ON w.workstation_id=wc_mod.workstation_id "
                   "AND wc_mod.parameter = 'Modules' "
                   f"WHERE w.workstation_id = {workstation[0]}")
            
            query = self.db.dbQuery(sql)
            # Use tuple unpacking safely
            row = query.first()
            id_val, hostname, status, description, isActive, mainActions, modules = row

            self.idLabel.setText(str(id_val))
            self.hostnameLabel.setText(hostname)
            self.statusCB.setCurrentIndex(0 if status == 'closed' else 1)
            self.descriptionLabel.setText(description)
            self.isActive.setChecked(str(isActive) == '1')
            self.editBtn.setText('Update Workstation')

            # Use Base Class helper methods
            if mainActions: self.sync_checkboxes(mainActions, self.action_map)
            if modules: self.sync_checkboxes(modules, self.module_map)

        else:
            # Get new ID logic
            sql = 'SELECT MAX(workstation_id) from workstations'
            query = self.db.dbQuery(sql)
            max_id = query.first()[0]
            # Handle case where table is empty
            newId = (int(max_id) + 1) if max_id is not None else 1
            
            self.idLabel.setText(str(newId))
            self.hostnameLabel.setText('')
            self.statusCB.setCurrentIndex(0)
            self.descriptionLabel.setText('')
            self.isActive.setChecked(False)
            self.editBtn.setText('Add Workstation')

            self.sync_checkboxes("", self.action_map)
            self.sync_checkboxes("", self.module_map)

    def validate_fields(self):
        return self.validate_required_fields([
            ("hostname", self.hostnameLabel.text()),
            ("description", self.descriptionLabel.text())
        ])

    def perform_save(self):
        status = self.statusCB.currentText()
        hostName = self.hostnameLabel.text()
        description = self.descriptionLabel.text()
        id_val = self.idLabel.text()
        active = "1" if self.isActive.isChecked() else "0"

        # Use Base Class helper
        mainActionStr = self.create_csv_from_checkboxes(self.action_map)
        moduleStr = self.create_csv_from_checkboxes(self.module_map)

        if 'Update' in self.editBtn.text():
            # Update Workstation
            prep = self.db.prepare(f"UPDATE {self.schema}.WORKSTATIONS SET "
                "hostname=:hostname, status=:status, description=:description, active=:active "
                "WHERE workstation_id=:id")
            
            data = {':hostname': hostName, ':status': status, ':description': description, 
                    ':active': active, ':id': id_val}
            self.db.dbExecPrepared(prep, data)

            # Update Configs
            self.db.dbExec(f"UPDATE {self.schema}.WORKSTATION_CONFIGURATION SET "
                           f"parameter_value='{mainActionStr}' WHERE workstation_id={id_val} AND parameter='MainActions'")
            self.db.dbExec(f"UPDATE {self.schema}.WORKSTATION_CONFIGURATION SET "
                           f"parameter_value='{moduleStr}' WHERE workstation_id={id_val} AND parameter='Modules'")
        else:
            # Insert Workstation
            prep = self.db.prepare(f"INSERT INTO {self.schema}.WORKSTATIONS "
                "(workstation_id, hostname, status, description, active) VALUES "
                "(:id, :hostname, :status, :description, :active)")
            
            data = {':id': id_val, ':hostname': hostName, ':status': status, 
                    ':description': description, ':active': active}
            self.db.dbExecPrepared(prep, data)

            # Insert Configs
            sql = (f"INSERT INTO {self.schema}.WORKSTATION_CONFIGURATION (workstation_id, parameter, parameter_value) "
                   f"VALUES ({id_val}, 'MainActions', '{mainActionStr}'), "
                   f"({id_val}, 'Modules', '{moduleStr}')")
            self.db.dbExec(sql)