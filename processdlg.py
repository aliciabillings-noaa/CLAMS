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
.. module:: CLAMSmain

    :synopsis: CLAMSmain presents the main CLAMS application window.
    It is the entry point for the CLAMS catch processing application.

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
"""

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from ui import ui_ProcessDlg
import eventseldlg


'''
ProcessDlg is shown when a user clicks "Enter Catch" on the main
CLAMS dialog to start processing the catch. It allows the user to choose
the active event, or they can click edit past event which will present
the event selection dialog (EventSelDlg)
'''

class ProcessDlg(QDialog, ui_ProcessDlg.Ui_processDlg):

    def __init__(self, haul, time, parent=None):
        super(ProcessDlg, self).__init__(parent)
        self.setupUi(self)

        self.parent = parent

        #  connect our signals
        self.procBtn.clicked.connect(self.exit)
        self.editBtn.clicked.connect(self.edit)
        self.cancelBtn.clicked.connect(self.cancel)

        self.haulLabel.setText(haul)
        self.timeLabel.setText(time)

        if haul=='0':
            self.procBtn.setEnabled(False)

    def edit(self):
        hlDialog = eventseldlg.EventSelDlg(self.parent, catchOnly=True)
        hlDialog.newEventBtn.setEnabled(False)
        if hlDialog.exec():
            self.activeEvent = hlDialog.activeEvent
            self.accept()


    def cancel(self):
        self.reject()


    def exit(self):
        self.activeEvent = self.haulLabel.text()
        self.accept()


