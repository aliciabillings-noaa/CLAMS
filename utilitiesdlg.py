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
    :module:: UtilitiesDlg

    :synopsis: UtilitiesDlgvis launched when someone clicks the ""Utilities""
               button on the main screen. Most of the utilities are out of date
               and 2 of the 3 buttons are disabled."

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

from PyQt6 import QtSql
from PyQt6.QtWidgets import QDialog, QApplication
import devicesetupdlg
from deprecated import streamloaddlg
from ui import ui_UtilitiesDlg

class UtilitiesDlg(QDialog, ui_UtilitiesDlg.Ui_utilitiesdlg):

    def __init__(self, parent=None):
        super(UtilitiesDlg, self).__init__(parent)
        self.setupUi(self)

        self.db=parent.db
        self.ship=parent.ship
        self.survey=parent.survey
        self.settings=parent.settings
        self.workStation=parent.workStation

        #  set up signals
        #self.connect(self.exportFSCSBtn, SIGNAL("clicked()"), self.createFSCSfiles)
        self.loadStreamBtn.clicked.connect(self.loadStreamData)
        self.setupBtn.clicked.connect(self.setupDevices)
        self.doneBtn.clicked.connect(self.doneClicked)
        
        self.exportFSCSBtn.setEnabled(False)
        self.loadStreamBtn.setEnabled(False)

        self.show()


#    def createFSCSfiles(self):
#        '''
#        createFSCSfiles creates a set of csv files that mimic the output of FSCS 1.x
#        '''
#
#        #  get the Haul
#
#        hlDialog = eventseldlg.EventSelDlg(self)
#        hlDialog.newEventBtn.hide()
#        if not hlDialog.exec_():
#            #  user cancelled action
#            return
#
#        self.activeHaul = hlDialog.activeEvent
#        self.doneBtn.setEnabled(False)
#        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
#        FSCSload = fscsload.Fscsload(self)
#        FSCSload.makeFiles()
#        QApplication.restoreOverrideCursor()
#        self.doneBtn.setEnabled(True)
#
#        if (not FSCSload.errormsg == None):
#            QMessageBox.critical(self, "ERROR", "<font size = 10>FSCS file creation failed." + FSCSload.errormsg)
#        else:
#            QMessageBox.information(self, "INFO", "<font size = 10>FSCS files successfully exported to " + FSCSload.folder)


    def setupDevices(self):
        dlg = devicesetupdlg.DeviceSetupDlg(self)
        dlg.exec()


    def loadStreamData(self):
        '''
        readSCSStreamfiles uploads SCS stream data into clams, in case trawl event hiccups.
        '''

        #  get the Haul
        sql = ("SELECT HAUL.HAUL, HAUL_DATA.PARAMETER_VALUE FROM HAUL, " +
                                "HAUL_DATA  WHERE HAUL_DATA.SHIP=HAUL.SHIP and HAUL_DATA.SURVEY=HAUL.SURVEY " +
                                "and HAUL_DATA.HAUL=HAUL.HAUL and " +
                                "HAUL_DATA.SHIP = " + self.ship + " and " +
                                "HAUL_DATA.SURVEY = " + self.survey + " and " +
                                "HAUL_DATA.HAUL_PARAMETER='Haulback' and partition in ('Codend','Codend_1')")

        query = self.db.dbQuery(sql)
        Hauls = []
        EQTimes = []
        for haul, haulData in query:
            Hauls.append(haul)
            EQTimes.append(haulData)

        hlDialog = haulseldialog.HaulSelDialog(Hauls, EQTimes, self.db, self)
        hlDialog.editBtn.setText('Load Stream Data')
        hlDialog.notBtn.hide()
        hlDialog.haulTab.setCurrentIndex(1)
        hlDialog.haulTab.setTabEnabled(0, False)
        if not hlDialog.exec():
            #  user cancelled action
            return


        self.activeHaul = hlDialog.activeHaul
        loaddlg = streamloaddlg.StreamLoadDlg(self)
        loaddlg.exec()

    def doneClicked(self):
        self.reject()


    def closeEvent(self, event=None):
        self.reject()



if __name__ == "__main__":

    import sys
    app = QApplication(sys.argv)

    db = QtSql.QSqlDatabase.addDatabase("QODBC")
    db.setDatabaseName('mbdev')
    db.setUserName('mbdev')
    db.setPassword('pollock')
    db.schema = 'mbdev'
    db.open()

    form = UtilitiesDlg()
    app.exec()
