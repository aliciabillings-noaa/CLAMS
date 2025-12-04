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
.. module:: donedlg

    :synopsis: donedlg is a dialog that collects the gear performance and overall comments from a tow;
                used by the NWFSC;
                created by Alicia Billings <alicia.billings@noaa.gov>

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assesment and Conservation Engineering Group (MACE)
|
| Author:
|       Kresimir Williams   <kresimir.williams@noaa.gov>
| Maintained by:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
|       Mike Levine   <mike.levine@noaa.gov>
|       Nathan Lauffenburger   <nathan.lauffenburger@noaa.gov>
"""

from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from ui import ui_SWFSCCatchHome
import swfsc.UnsortedCatch as unsortedCatch
import CLAMScatch

class CatchHome(QDialog, ui_SWFSCCatchHome.Ui_SWFSCCatchHome):

    def __init__(self, parent=None):
        super(CatchHome, self).__init__(parent)
        self.setupUi(self)

        self.db = parent.db
        self.sensorMonitor = parent.sensorMonitor
        self.workStation = parent.workStation
        self.activeHaul = parent.activeHaul
        self.survey = parent.survey
        self.ship = parent.ship
        self.settings = parent.settings
        self.activePartition = parent.activePartition
        self.errorSounds = parent.errorSounds
        self.errorIcons = parent.errorIcons
        self.scientist = parent.scientist
        self.deviceData = parent.deviceData
        self.schema = parent.schema

        #  set the event number
        self.haulNum.setText(self.activeHaul)

        #  set up some colors
        self.black = QPalette()
        self.black.setColor(QPalette.ColorRole.ButtonText,QColor(0, 0, 0))

        # set up button colors
        self.unsortedBtn.setPalette(self.black)
        self.sortedBtn.setPalette(self.black)
        self.unsortedBtn.setEnabled(True)
        self.sortedBtn.setEnabled(True)

        # set up signals and slots
        self.unsortedBtn.clicked.connect(self.getUnsorted)
        self.sortedBtn.clicked.connect(self.getSorted)

    def getUnsorted(self):
        #  show the catch form
        unsorted = unsortedCatch.UnsortedCatch(self)
        unsorted.exec()

    def getSorted(self):
        #  show the catch form
        catchWindow = CLAMScatch.CLAMSCatch(self)
        catchWindow.exec()
