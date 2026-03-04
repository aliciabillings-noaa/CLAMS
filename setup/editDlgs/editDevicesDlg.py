from ui import ui_EditDevicesDlg
from .baseEditDlg import BaseEditDlg

class editDevicesDlg(BaseEditDlg, ui_EditDevicesDlg.Ui_EditDevicesDlg):

    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.setupUi(self)

        # Wire the buttons
        self.setup_base()

        # Populate dropdowns
        self.deviceInterfaces = []

        sql = "SELECT device_interface from device_interfaces"
        query = self.db.dbQuery(sql)
        for interfaces, in query:
            self.deviceInterfaces.append(interfaces)
        self.deviceInterfaceCB.addItems(self.deviceInterfaces)

    def setUp(self, device):
        if device:
            self.idLabel.setText(device[0])
            self.deviceNameLabel.setText(device[1])
            self.modelLabel.setText(device[2])
            self.serialNumLabel.setText(device[3])
            self.description.setText(device[4])
            self.isActive.setChecked(device[5] == 'Yes')
            self.deviceInterfaceCB.setCurrentIndex(self.deviceInterfaces.index(device[6]))
        else:
            # Get new ID logic
            sql = 'SELECT MAX(device_id) from devices'
            query = self.db.dbQuery(sql)
            max_id = query.first()[0]
            # Handle case where table is empty
            newId = (int(max_id) + 1) if max_id is not None else 1

            self.idLabel.setText(str(newId))
            self.deviceNameLabel.setText('')
            self.modelLabel.setText('')
            self.serialNumLabel.setText('')
            self.description.setText('')
            self.isActive.setChecked(False)
            self.deviceInterfaceCB.setCurrentIndex(-1)
        

    def validate_fields(self):
        return self.validate_required_fields([
            ("deviceName", self.deviceNameLabel.text())
        ])

    def getData(self):
        # This method can be used if you want to gather all data at once before saving
        print('stub')

    def perform_save(self):
        sql = (f"INSERT INTO {self.schema}.devices (device_id, device_name, model, "
               "serial_number, description, active, device_interface) "
               f"VALUES ({self.idLabel.text()},'{self.deviceNameLabel.text()}', " 
               f"'{self.modelLabel.text()}', '{self.serialNumLabel.text()}', "
               f"'{self.description.toPlainText()}' , {1 if self.isActive.isChecked() else 0}, "
               f"'{self.deviceInterfaceCB.currentText()}')")
        self.db.dbExec(sql)
    
    def update(self):
        sql = (f"UPDATE {self.schema}.devices SET device_name='{self.deviceNameLabel.text()}', "
                f"model='{self.modelLabel.text()}', serial_number='{self.serialNumLabel.text()}', "
                f"description='{self.description.toPlainText()}', active={1 if self.isActive.isChecked() else 0}, "
                f"device_interface='{self.deviceInterfaceCB.currentText()}' WHERE device_id={self.idLabel.text()}")
        self.db.dbExec(sql)