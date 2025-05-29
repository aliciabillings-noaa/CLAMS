

#  import dependent modules
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
import serial
from . import serial_scanwin
from .ui import ui_SelectWinPortDialog


class selectWinPortDialog(QDialog, ui_SelectWinPortDialog.Ui_SelectWinPortDialog):

    def __init__(self, defaultPort=None, defaultBaud=None, showAll=False, title=None, parent=None):
        #  initialize the GUI
        super(selectWinPortDialog, self).__init__(parent)
        self.setupUi(self)

        self.allPorts = {}
        self.port = None
        self.baud = None

        #  set the title if provided
        if (title):
            self.titleLabel.setText(title)

        #  get the list of COM ports
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        for port, desc, hwid in sorted(serial_scanwin.comports(not showAll)):
             # test open to determine port status
            try:
                serial.Serial(port)
            except serial.serialutil.SerialException:
                status = "In use"
            else:
                status = "Ready"
            self.allPorts[port] = (port, desc, hwid, status)

        #  add ports to the combo box and update details
        if (len(self.allPorts) > 0):
            self.cbPorts.addItems(self.allPorts.keys())
            if (defaultPort):
                idx = self.cbPorts.findText(defaultPort)
                if (idx >= 0):
                    self.cbPorts.setCurrentIndex(idx)
            if (defaultBaud):
                idx = self.cbBaud.findText(str(defaultBaud))
                if (idx >= 0):
                    self.cbBaud.setCurrentIndex(idx)
            self.portSelected(self.cbPorts.currentText())

        #  connect the signals
        self.cbPorts.currentTextChanged.connect(self.portSelected)
        self.pbCancel.clicked.connect(self.cancelClicked)
        self.pbOK.clicked.connect(self.okClicked)

        QApplication.restoreOverrideCursor()


    def portSelected(self, portName):

        portName = str(portName)
        self.descLabel.setText(self.allPorts[portName][1])
        self.idLabel.setText(self.allPorts[portName][2])
        self.statusLabel.setText(self.allPorts[portName][3])


    def okClicked(self):

        self.port=str(self.cbPorts.currentText())
        self.baud=int(self.cbBaud.currentText())
        self.accept()


    def cancelClicked(self):

        self.port=None
        self.baud=None
        self.reject()


if __name__ == "__main__":

    import sys
    app = QApplication(sys.argv)
    form = selectWinPortDialog()
    form.show()
    app.exec()
