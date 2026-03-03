from ui import ui_DevicesDlg
import setup.editDlgs.editMeasurementDlg as editMeasurementDlg
from PyQt6.QtWidgets import QTableWidgetItem
# Import the base class created above
from .baseTableDlg import BaseTableDlg 

class devicesDlg(BaseTableDlg, ui_DevicesDlg.Ui_DevicesDlg):

    def __init__(self, db, parent=None):
        # Initialize Base Logic
        super().__init__(db, parent)
        # Initialize UI (from the generated file)
        self.setupUi(self)
        self.workstationId = 0

        # Create the specific child dialog
        self.dialog = editMeasurementDlg.editMeasurement(self.db, parent=self)
        self.dialog.changed.connect(self.populate_table)

        # WIRE IT UP: Pass the specific table and dialog to the Base
        self.setup_base(self.devicesTable, self.dialog)

    # --- Implement the Hooks ---
    def setCurrWorkstation(self, id):
        self.workstationId = id
        self.dialog.setCurrWorkstation(id)

    def get_select_sql(self):
        return "SELECT device_id, device_name, model, serial_number, description, active, device_interface FROM " \
            + self.schema + ".devices ORDER BY device_id"

    def fill_row(self, row_idx, row_data):
        # Unpack the data returned by the query
        id, name, model, serialNum, description, active, interface = row_data
                
        self.table.setItem(row_idx, 0, QTableWidgetItem(str(id)))
        self.table.setItem(row_idx, 1, QTableWidgetItem(name))
        self.table.setItem(row_idx, 2, QTableWidgetItem(model))
        self.table.setItem(row_idx, 3, QTableWidgetItem(serialNum))
        self.table.setItem(row_idx, 4, QTableWidgetItem(description))
        self.table.setItem(row_idx, 5, QTableWidgetItem(str(active)))
        self.table.setItem(row_idx, 6, QTableWidgetItem(interface))

    def get_data_for_edit(self, row_idx):
        # Workstation dialog only sends the ID (col 0) to the edit window
        return [
            self.table.item(row_idx, 0).text(),
            self.table.item(row_idx, 1).text(),
            self.table.item(row_idx, 2).text(),
            self.table.item(row_idx, 3).text(),
            self.table.item(row_idx, 4).text(),
            self.table.item(row_idx, 5).text(),
            self.table.item(row_idx, 6).text()
        ]