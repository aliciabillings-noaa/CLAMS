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
    :module:: sbeSetInterval

    :synopsis: The dialog is presented when the user clicks ""Set Sampling Info""
                in the ""Configure"" menu in CLAMSsbeDownloader. It gets the
                interval from the user and triggers the command to set the new
                sampling interval on the connected SBE.

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assesment and Conservation Engineering Group (MACE)
|
| Author:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
| Maintained by:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
|       Mike Levine   <mike.levine@noaa.gov>
|       Nathan Lauffenburger   <nathan.lauffenburger@noaa.gov>
        Melina Shak <melina.shak@noaa.gov>
"""

from PyQt6.QtWidgets import QDialog, QApplication
from PyQt6.QtCore import pyqtSignal
from .ui import ui_sbeSetInterval

class sbeSetInterval(QDialog, ui_sbeSetInterval.Ui_sbeSetInterval):

    sbeSetIntervalSignal = pyqtSignal(int, bool)

    def __init__(self, parent=None):
        #  initialize the parents
        super(sbeSetInterval, self).__init__(parent)
        self.setupUi(self)

        self.lastVal = 0

        #  set up signals
        self.spinInterval.valueChanged[int].connect(self.spinChanged)
        self.pbOK.clicked.connect(self.okClicked)
        self.pbCancel.clicked.connect(self.cancelClicked)


    def setInterval(self, interval, rto):

        self.spinInterval.setValue(int(interval))
        self.lastVal = self.spinInterval.value()
        self.cbRTO.setChecked(rto)


    def spinChanged(self, val):
        #  if the interval is set to 1 or 2, change it to 0
        if (val < 3) and (self.lastVal > 2):
            self.spinInterval.setValue(0)
        elif (val < 3) and (self.lastVal == 0):
            self.spinInterval.setValue(3)

        self.lastVal = self.spinInterval.value()


    def okClicked(self):

        self.sbeSetIntervalSignal.emit(self.spinInterval.value(), self.cbRTO.isChecked())
        self.accept()


    def cancelClicked(self):
        self.accept()


if __name__ == "__main__":

    import sys
    app = QApplication(sys.argv)
    form = sbeSetInterval()
    form.show()
    app.exec()
