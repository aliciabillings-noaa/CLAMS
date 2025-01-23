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
.. module:: ClipDlg

    :synopsis: ClipDlg presents a dialog to enter the cell number for a finclip

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
| Created by:
|       Alicia Billings - alicia.billings@noaa.gov
|       date: April 2019
| Updated January 2025 by:
|       Alicia Billings <alicia.billings@noaa.gov>
|           specific updates:
|               - PyQt import statement
|               - signal/slot connections
|               - added some function explanation
|               - fixed any PEP8 issues
|               - added a main to test if works (commented out)
|
| NOTE: cannot test this until it is called with parent values
"""

from PyQt6.QtWidgets import *
from ui import ui_ClipDlg
from sys import argv
import numpad


class ClipDlg(QDialog, ui_ClipDlg.Ui_Dialog):
    def __init__(self, parent=None):
        super(ClipDlg, self).__init__(parent)
        self.setupUi(self)

        self.oto_present = True

        self.result = ()

        #  connect signals
        self.pb_clip.clicked.connect(self.get_cell_num)

        #  if there is already an entry, reset the button text
        self.set_btn_txt()

    def setup(self, parent):
        """
        does nothing
        :param parent: not used in this function
        :return: none
        """
        pass

    def set_btn_txt(self):
        """
        sets the button text
        :return: none
        """
        self.pb_clip.setText("Click here")

    def get_cell_num(self):
        """
        opens up the number pad to have user enter the cell number
        :return: none
        """
        rst = numpad.NumPad()
        rst.exec()
        self.pb_clip.setText(rst.value)
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
    form = ClipDlg()
    form.show()
    #  and start the application...
    app.exec()
"""
