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
.. module:: ScaleCardDlg

    :synopsis: Dialog to capture information from a scale sample

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assessment and Conservation Engineering Group (MACE)
|
| Author:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
| Maintained by:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
|       Mike Levine   <mike.levine@noaa.gov>
|       Nathan Lauffenburger   <nathan.lauffenburger@noaa.gov>
| Updated February 2025 by:
|       Alicia Billings <alicia.billings@noaa.gov>
|           specific updates:
|               - PyQt import statement
|               - signal/slot connections
|               - added some function explanation
|               - fixed any PEP8 issues
|               - added a main to test if works (commented out)
|
"""

from PyQt6.QtWidgets import *
from ui import ui_ScaleCardDlg
import numpad
from sys import argv


class ScaleCardDlg(QDialog, ui_ScaleCardDlg.Ui_scalecardDlg):
    def __init__(self,  parent=None):
        super(ScaleCardDlg, self).__init__(parent)
        self.setupUi(self)

        # variable declarations
        self.card = None
        self.pos = None
        self.result = ()

        # signal/slot connection
        self.cardBtn.clicked.connect(self.getCard)
        self.positionBtn.clicked.connect(self.getPosition)
        self.doneBtn.clicked.connect(self.goExit)
        self.numpad = numpad.NumPad(self)

    def setup(self, parent):
        pass
        
    def getCard(self):
        self.numpad.msgLabel.setText("Punch in the Card number")
        if not self.numpad.exec():
            return
        self.card = self.numpad.value
        self.cardBtn.setText(self.card)
        
    def getPosition(self):
        self.numpad.msgLabel.setText("Punch in the Card position")
        if not self.numpad.exec():
            return
        self.pos = self.numpad.value
        self.positionBtn.setText(self.pos)
        
    def goExit(self):
        # todo: there should be a check here since they have to enter both...
        # exit check
        self.close()
        
    def closeEvent(self, event):

        if not self.card or not self.pos:
            self.reject()
        else:
            self.result = (True, self.card + "_" + self.pos)
            self.accept()


"""
if __name__ == "__main__":
    #  create an instance of QApplication
    app = QApplication(argv)
    #  create an instance of the dialog
    form = ScaleCardDlg()
    #  show it
    form.show()
    #  and start the application...
    app.exec()
"""
