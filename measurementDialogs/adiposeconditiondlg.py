
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from ui import ui_AdiposeCondition

"""
.. module:: AdiposeConditionDlg

    :synopsis: Dialog to present yes/no for taking an otolith

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assessment and Conservation Engineering Group (MACE)
|
| Author:
|       Melina Shak    <melina.shak@noaa.gov>
| Maintained by:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
|       Mike Levine   <mike.levine@noaa.gov>
|       Nathan Lauffenburger   <nathan.lauffenburger@noaa.gov>
|       Melina Shak    <melina.shak@noaa.gov>
"""

class AdiposeConditionDlg(QDialog, ui_AdiposeCondition.Ui_adiposeCondition):
    def __init__(self,  parent=None):
        super(AdiposeConditionDlg, self).__init__(parent)
        self.setupUi(self)

        # variable declarations
        self.result = ()

        self.clipped.clicked.connect(self.getResponse)
        self.intact.clicked.connect(self.getResponse)
        # todo: add not determined button for nwfsc
        

    def setup(self, parent):
        """
        does nothing
        :param parent: not used in this function
        :return: none
        """
        pass  

    def getResponse(self):
        """
        sets the result tuple to access from the calling dialog with the variables
        :return: self.accept the dialog and return
        """
        #  return the text
        self.result = (True, self.sender().text())
        self.accept() 

    def closeEvent(self, event):
        # query to clear and set new codes
        self.result = (False, '')
        self.reject()
