"""
addspecedlg is a modified version of messagedlg used for confirming the active
species for the CLAMS catch dlg.


"""


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
.. module:: addspecedlg

    :synopsis: addspecedlg is a modified version of messagedlg used for
               confirming the active species for the CLAMS catch dlg.

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assesment and Conservation Engineering Group (MACE)
|
| Author:
|       Rick Towler   <rick.towler@noaa.gov>
| Maintained by:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
|       Mike Levine   <mike.levine@noaa.gov>
|       Nathan Lauffenburger   <nathan.lauffenburger@noaa.gov>
"""

#  imports
from PyQt6.QtGui import *
from PyQt6.QtWidgets import QDialog
from ui import ui_MessageDlg


class addspecedlg(QDialog, ui_MessageDlg.Ui_messageDlg):
    def __init__(self,  parent=None):
        super(addspecedlg, self).__init__(parent)
        self.setupUi(self)
        self.btn_1.clicked.connect(self.goNo)
        self.btn_2.clicked.connect(self.goYes)
        self.btn_3.clicked.connect(self.goYes)

    def setMessage(self, icon, sound, string, mode=''):
        sound.play()


        self.btn_1.setText('OK')
        self.btn_2.hide()
        self.btn_3.hide()

        self.msgLabel.setText(string)
#        font = QFont()
#        font.setBold(True)
#        font.setPointSize(25)
#        self.msgLabel.setFont(font)
        try:
            self.iconLabel.setMovie(icon)
            icon.start()
        except:
            self.iconLabel.setPixmap(icon)

    def goYes(self):
        self.response = self.sender().text()
        self.accept()

    def goNo(self):
        self.reject()





