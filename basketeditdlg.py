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
.. module:: ABLImMatSalmonSpecialStudiesDlg

    :synopsis: ABLImMatSalmonSpecialStudiesDlg presents a dialog to choose optional special studies
                performed; specific for ABL

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
| Updated January 2025 by:
|       Alicia Billings <alicia.billings@noaa.gov>
|           specific updates:
|               - PyQt import statement
|               - signal/slot connections
|               - moved variable declarations into __init__
|               - added some function explanation
|               - fixed any PEP8 issues
|               - added a main to test if works (commented out)
|
| NOTE: cannot test this until it is called with parent values
"""

from PyQt6.QtWidgets import *
from ui import ui_BasketEditDlg
import numpad


class BasketEditDlg(QDialog, ui_BasketEditDlg.Ui_basketeditDlg):
    def __init__(self, header,  items,  parent=None):
        super(BasketEditDlg, self).__init__(parent)
        self.setupUi(self)

        self.keep = None
        self.transDevice = None
        self.okFlag = False

        self.validList = parent.validList
        self.typeDlg = parent.typeDlg
        self.sensorMonitor = parent.sensorMonitor
        self.devices = parent.devices
        self.sounds = parent.sounds
        self.errorIcons = parent.errorIcons
        self.errorSounds = parent.errorSounds

        # set up edit basket table
        self.editBasket.setColumnCount(len(header))
        self.editBasket.setRowCount(1)
        self.editBasket.verticalHeader().setVisible(False)
#        self.editBasket.setColumnWidth(0, 150)
#        self.editBasket.setColumnWidth(1, 116)
#        self.editBasket.setColumnWidth(2, 116)
#        self.editBasket.setColumnWidth(3, 116)
        for i in range(len(header)):
            self.editBasket.setHorizontalHeaderItem(i, QTableWidgetItem(header[i]))
            self.editBasket.setItem(0, i, QTableWidgetItem(items[i]))

        self.weight = items[1]
        self.count = items[2]
        self.basketType = items[3]
        self.numpad = numpad.NumPad(self)

        # signal/slot connections
        self.editBasket.itemSelectionChanged.connect(self.getEdit)
        self.okBtn.clicked.connect(self.getOK)
        self.cancelBtn.clicked.connect(self.getCancel)
        self.sensorMonitor.SensorDataReceived.connect(self.getAuto)

    def getEdit(self):
        """
        brings up a number pad (if selected weight or count edits) or a way to choose basket type
        changes the text in the table to be saved
        :return: none
        """
        col = self.editBasket.currentColumn()
        if col == 1:
            # selected weight
            self.numpad.msgLabel.setText("Enter the New Weight")
            if not self.numpad.exec():
                return
            self.weight = self.numpad.value
            self.editBasket.setItem(0, 1, QTableWidgetItem(self.weight))
        elif col == 2:
            # selected count
            currentCount = self.editBasket.currentItem().text()
            if currentCount == '-':
                self.basketType = "Count"
                self.editBasket.setItem(0, 3, QTableWidgetItem(self.basketType))
            self.numpad.msgLabel.setText("Enter the New Count")
            if not self.numpad.exec():
                return
            self.count = self.numpad.value
            self.editBasket.setItem(0, 2, QTableWidgetItem(self.count))
        elif col == 3:
            # selected basket type
            self.typeDlg.exec()
            self.basketType = self.typeDlg.basketType
            self.editBasket.setItem(0, 3, QTableWidgetItem(self.basketType))
            if self.basketType == 'Count':
                self.count = self.typeDlg.count
                self.editBasket.setItem(0, 2, QTableWidgetItem(self.count))
            else:
                self.count = '-'
                self.editBasket.setItem(0, 2, QTableWidgetItem('-'))

    def getAuto(self, device, val):
        """
        gets information from the device that sent an entry (should be only scale here)
        :param device: device that sent the entry
        :param val: value that is sent
        :return: none
        """
        self.weight = val
        self.editBasket.setItem(0, 0, QTableWidgetItem(self.weight))
        self.transDevice = device
        self.sounds[self.devices.index(device)].play()

    def getOK(self):
        """
        sets the okFlag to true and closes the dialog
        :return: none
        """
        self.okFlag = True
        self.done(1)

    def getCancel(self):
        """
        sets the okFlag to false and closes the dialog
        :return: none
        """
        self.okFlag = False
        self.done(1)
