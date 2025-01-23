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
.. module:: AdiposeYesNoDlg

    :synopsis: Adapted from finclipyesnodlg.py for use by NWFSC;
                Keeps track of whether a salmon has an adipose fin or not

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
"""

from PyQt6.QtWidgets import *
from ui import ui_YesNoDlg
from sys import argv


class AdiposeYesNoDlg(QDialog, ui_YesNoDlg.Ui_YesNoDlg):
    def __init__(self, parent=None):
        super(AdiposeYesNoDlg, self).__init__(parent)
        self.setupUi(self)

        # variable declarations
        self.result = ()

        # signal/slot connection
        self.yesBtn.clicked.connect(self.getResponse)
        self.noBtn.clicked.connect(self.getResponse)

        #  set the caption
        self.setCaption('Is there an adipose fin present?')

    def setup(self, parent):
        """
        does nothing
        :param parent: not used in this function
        :return: none
        """
        pass

    def setCaption(self, text):
        """
        sets the message label to the passed text
        :param text: text to set label to
        :return: none
        """
        self.msgLabel.setText(text)

    def getResponse(self):
        """
        sets the result tuple to access from the calling dialog with the variables
        :return: self.accept the dialog and return
        """
        #  return the text
        self.result = (True, self.sender().text())
        self.accept()

    def closeEvent(self, event):
        """
        sets the result tuple to access from the calling dialog
        :return: self.reject and return
        """
        self.result = (False, '')
        self.reject()


"""
if __name__ == "__main__":
    #  create an instance of QApplication
    app = QApplication(argv)
    #  create an instance of the dialog
    form = AdiposeYesNoDlg()
    #  show it
    form.show()
    #  and start the application...
    app.exec()
"""
