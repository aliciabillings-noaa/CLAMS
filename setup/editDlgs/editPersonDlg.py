from ui import ui_EditPersonnelDlg
from .baseEditDlg import BaseEditDlg

class editPersonDlg(BaseEditDlg, ui_EditPersonnelDlg.Ui_EditPersonnelDlg):

    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.setupUi(self)

        # Wire the buttons to the Base logic
        self.setup_base()

    def setUp(self, currPerson):
        if currPerson and len(currPerson) > 0:
            self.scientistLabel.setText(currPerson[0])
            self.affiliationLabel.setText(currPerson[1])
            self.isActive.setChecked(currPerson[2] == 'Yes')
            self.editBtn.setText('Update Personnel')
        else:
            self.scientistLabel.setText('')
            self.affiliationLabel.setText('')
            self.isActive.setChecked(False)
            self.editBtn.setText('Add Personnel')

    def validate_fields(self):
        # Use the Base helper to check for empty fields
        return self.validate_required_fields([
            ("Scientist", self.scientistLabel.text()),
            ("Affiliation", self.affiliationLabel.text())
        ])

    def perform_save(self):
        scientist = self.scientistLabel.text()
        affiliation = self.affiliationLabel.text()
        isActive = 1 if self.isActive.isChecked() else 0
        
        if 'Update' in self.editBtn.text():
            sql = (f"UPDATE {self.schema}.personnel SET active={isActive} "
                   f"WHERE scientist='{scientist}' and affiliation='{affiliation}'")
        else:
            sql = (f"INSERT INTO {self.schema}.personnel (scientist, affiliation, active) "
                   f"VALUES ('{scientist}', '{affiliation}', '{isActive}')")

        self.db.dbExec(sql)