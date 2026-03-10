from ui import ui_WorkstationDlg
import setup.editDlgs.editWorkstationDlg as editWorkstationDlg
from PyQt6.QtWidgets import QTableWidgetItem
# Import the base class created above
from .baseTableDlg import BaseTableDlg 
import setup.table.measurementsDlg as measurementsDlg

class workstationDlg(BaseTableDlg, ui_WorkstationDlg.Ui_WorkstationDlg):

    def __init__(self, db, parent=None):
        # Initialize Base Logic
        super().__init__(db, parent)
        # Initialize UI (from the generated file)
        self.setupUi(self)

        # Create the specific child dialog
        dialog = editWorkstationDlg.editWorkstationDlg(self.db, parent=self)
        dialog.changed.connect(self.populate_table)

        # create measurement dialog
        self.measurementDialog = measurementsDlg.measurementsDlg(self.db, parent=self)

        # WIRE IT UP: Pass the specific table and dialog to the Base
        self.setup_base(self.workstationTable, dialog)
        self.editMeasurements.clicked.connect(self.openMeasurements)

    # --- Implement the Hooks ---

    def get_select_sql(self):
        return (f"SELECT workstation_id, hostname, description, active "
                f"FROM {self.schema}.workstations ORDER BY workstation_id")

    def fill_row(self, row_idx, row_data):
        # Unpack the data returned by the query
        w_id, hostname, description, active = row_data
        
        isActive = 'Yes' if str(active) == '1' else 'No'
        
        self.table.setItem(row_idx, 0, QTableWidgetItem(str(w_id)))
        self.table.setItem(row_idx, 1, QTableWidgetItem(hostname))
        self.table.setItem(row_idx, 2, QTableWidgetItem(description))
        self.table.setItem(row_idx, 3, QTableWidgetItem(isActive))

    def get_data_for_edit(self, row_idx):
        # Workstation dialog only sends the ID (col 0) to the edit window
        return [self.table.item(row_idx, 0).text()]

    def on_selection_change(self, has_selection):
        # This automatically runs when selection changes in the Base class
        workstationId = self.table.item(self.currentRow, 0).text()
        self.measurementDialog.setCurrWorkstation(workstationId)
        self.editMeasurements.setEnabled(has_selection)
    
    def openMeasurements(self):
        self.measurementDialog.populate_table()
        self.measurementDialog.exec()
