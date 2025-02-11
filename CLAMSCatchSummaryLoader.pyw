#!/usr/bin/env python
"""
CLAMSCatchSummaryLoader is a simple application that queries the underlying CLAMS
data tables, creates summary information, and then populates the catch summary table.

If the provided username is "clamsbase2" it is assumed that

This program must be run after processing OR editing a haul to load/update the data
in the catch summary table.
"""

#  import dependent modules
import sys
import os
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *

import dbConnection
import Clamsbase2Functions
from ui import ui_CatchSummaryLoader


class CLAMSCatchSummaryLoader(QMainWindow, ui_CatchSummaryLoader.Ui_MainWindow):

    def __init__(self, dataSource, schema, user, password, parent=None):
        super(CLAMSCatchSummaryLoader, self).__init__(parent)
        self.setupUi(self)

        #  Initialize variables and define constants
        self.initializing = True

        #  connection parameters
        self.dbName  = dataSource
        self.schema = schema
        self.userID  = user
        self.pswd  =  password

        #  create an instance of our dbConnection class
        self.db = dbConnection.dbConnection(self.dbName, self.userID, self.pswd)
        self.db.bioSchema = self.schema

        #  restore the application state
        self.appSettings = QSettings('afsc.noaa.gov', 'CLAMSCatchSummaryLoader')
        size = self.appSettings.value('winsize', QSize(420,190)).toSize()
        self.resize(size)
        position = self.appSettings.value('winposition', QPoint(5,5)).toPoint()
        self.move(position)
        self.lastship = self.appSettings.value('lastship', '').toString()
        self.lastsurvey  = str(self.appSettings.value('lastsurvey', '').toString())

        #  add the COM port settings display in the status bar
        self.schemaLabel = QLabel('')
        self.statusbar.addPermanentWidget(self.schemaLabel)
        self.schemaLabel.setText('Schema: Not Connected')

        #  connect this GUI's button signals
        self.pbUpdateSurvey.clicked.connect(self.updateSurvey)
        self.pbUpdateEvent.clicked.connect(self.updateEvent)
        self.cbShip.clicked.connect(self.refreshSurveys)
        self.cbSurvey.clicked.connect(self.refreshEvents)

        #  start a timer event to connect to the database
        startTimer = QTimer(self)
        startTimer.setSingleShot(True)
        startTimer.timeout.connect(self.startApplication())
        startTimer.start(0)


    def startApplication(self):

        try:
            self.db.dbOpen()
        except Exception as err:
            QMessageBox.critical(self,"ERROR", "Unable to connect to the database. " + err.error)
            self.close()
            return

        #  update the schema name on the GUI
        self.schemaLabel.setText('Schema: ' + self.schema)

        #  set the initializing flag
        self.initializing = True

        #  clear the combobox
        self.cbShip.clear()

        #  populate the ship combo box
        sql = "SELECT ship FROM " + self.schema + ".ships"
        query = self.db.dbQuery(sql)
        for ship, in query:
            self.cbShip.addItem(ship)

        #  unset the initializing flag
        self.initializing = False

        #  unset the selection in our combobox to ensure that the next line fires an event
        self.cbShip.setCurrentIndex(-1)

        #  set to the last selected ship - otherwise to -1
        self.cbShip.setCurrentIndex(self.cbShip.findText(self.lastship, Qt.MatchExactly))


    def refreshSurveys(self, ship):

        #  make sure we don't execute when adding the first item to the combobox
        #  or when the combobox index is set to -1
        if (ship == '' or self.initializing):
            return

        #  set the initializing flag
        self.initializing = True

        # store the ship
        self.ship = ship
        self.appSettings.setValue('lastship', ship)

        #  clear the combobox
        self.cbSurvey.clear()

        #  populate the surveys combo box
        sql = ("SELECT survey FROM " + self.schema + ".surveys WHERE ship=" + ship +
                " AND ship <> 999 AND survey < 205000 AND survey > 190000 ORDER BY survey DESC")
        query = self.db.dbQuery(sql)
        for survey, in query:
            self.cbSurvey.addItem(survey)

        #  unset the initializing flag
        self.initializing = False

        #  unset the selection in our combobox to ensure that the next line fires an event
        self.cbSurvey.setCurrentIndex(-1)

        #  set to the last selected survey - otherwise to -1
        self.cbSurvey.setCurrentIndex(self.cbSurvey.findText(self.lastsurvey, Qt.MatchExactly))

        #  enable the GUI elements
        self.cbSurvey.setEnabled(True)
        self.pbUpdateSurvey.setEnabled(True)


    def refreshEvents(self, survey):

        #  make sure we don't execute when adding the first item to the combobox
        #  or when the combobox index is set to -1
        if (survey == '' or self.initializing):
            return

        # store the survey
        self.survey = survey
        self.appSettings.setValue('lastsurvey', survey)

        #  clear the combobox
        self.cbEvent.clear()

        #  populate the events combo box
        sql = ("SELECT event_id FROM " + self.schema + ".events WHERE ship=" + self.ship + " AND " +
                "survey=" + self.survey + " ORDER BY event_id DESC")
        query = self.db.dbQuery(sql)
        for event, in query:
            self.cbEvent.addItem(event)

        #  enable the GUI elements
        self.cbEvent.setEnabled(True)
        self.pbUpdateEvent.setEnabled(True)


    def updateSurvey(self):
        '''
        updateSurvey updates catch summary and histogram data for all events in
        the currently selected survey
        '''
        success = True
        events = [self.cbEvent.itemText(i) for i in range(self.cbEvent.count())]
        for event_id in events:
            #  update catch summary and histogram table for this event
            ok = self.updateCatchSummaryTable(self.ship, self.survey, event_id)
            if (not ok):
                success = False

        if (success):
            QMessageBox.information(self, 'Success', "Catch summary data updated for all events in survey " +
                    self.survey)
        else:
            QMessageBox.warning(self, 'Uh oh.', "Error updating catch summary data for one or more " +
                    "events in survey " + self.survey)


    def updateEvent(self):
        '''
        updateEvent updates catch summary and histogram data for the currently selected event
        '''

        event_id = self.cbEvent.currentText()
        if (event_id == ''):
            return

        #  update catch summary and histogram table for this event
        ok = self.updateCatchSummaryTable(self.ship, self.survey, event_id)

        if (ok):
            QMessageBox.information(self, 'Success', "Catch summary data updated for event " + event_id)
        else:
            QMessageBox.warning(self, 'Huh.', "Error updating catch summary data for event " + event_id)



    def updateCatchSummaryTable(self, ship, survey, event_id):
        '''
        updateCatchSummaryTable updates the catch summary data for the specified
        ship, survey, and event
        '''

        #  set the initial return state
        ok = True

        #  create an instance of clamsbase functions
        clamsFunctions = Clamsbase2Functions.Clamsbase2Functions(self.db, ship, survey)

        self.statusBar().showMessage("Updating Catch Summary for Event " + event_id);

        #  delete existing data for this event
        sql = ("DELETE FROM catch_summary WHERE ship=" + ship + " AND survey=" + survey +
                " AND event_id=" + event_id)
        self.db.dbExec(sql)

        #  find all the unique species samples
        sql = ("SELECT sample_id, parent_sample, partition, species_code, subcategory FROM samples " +
                "WHERE ship=" + ship + " AND survey=" + survey + " AND event_id=" + event_id +
                " AND sample_type='Species'")
        sampleQuery = self.db.dbQuery(sql)
        for sample_id, parent_sample, partition, species_code, subcategory in sampleQuery:
            #[sample id, species code, subcategory, sample id, WeightInHaul,SampledWeight,NumberInHaul,SampledNumer,FrequencyExpansion,InMix,WholeHauled]
            [status, vals]=clamsFunctions.computeCatchSummary(event_id, partition, species_code, subcategory)


            #  check if we successfully computed the summary data
            if status:
                vals = vals[0]
                #  yes - get species name
                sql = ("SELECT scientific_name, common_name FROM species WHERE species_code=" + species_code)
                sppQuery = self.db.dbQuery(sql)
                sci_name, common_name = sppQuery.first()

                #  then insert results into catch summary table
                sql = ("INSERT INTO catch_summary (ship,survey,event_id,partition,sample_id,parent_sample," +
                        "scientific_name,species_code,common_name,subcategory,weight_in_haul,sampled_weight," +
                        "number_in_haul,sampled_number,frequency_expansion,in_mix,whole_hauled) VALUES(" +
                        ship + "," + survey + "," + event_id + ",'" + partition + "'," + sample_id + "," +
                        parent_sample + ",'" + sci_name + "'," + species_code + ",'" + common_name +
                        "','" + subcategory + "'," + str(vals[4]) + "," + str(vals[5]) + "," +
                        str(vals[6]) + ","+str(vals[7]) + "," + str(vals[8]) + "," + str(vals[9]) +
                        "," + str(vals[10]) + ")")
                self.db.dbExec(sql)
            else:
                #  check to make sure there is an actionable error - computeCatchSummary can return false if there
                #  is a sample with no measurements which we silently ignore here as it isn't necessarily an error
                if (len(vals) > 0):
                    QMessageBox.warning(self, 'Attention!', "Error computing catch summary data for event " +
                            event_id + ". Error text:" + vals[2]  + vals[1])
                    ok = False
                    break


        #  clear the statusbar
        self.statusBar().clearMessage()

        #  ugly hack to force the UI to update
        QApplication.processEvents();

        return ok


    def closeEvent(self, event=None):

        if self.db:
            self.db.dbClose()
        self.appSettings.setValue('winposition', self.pos())
        self.appSettings.setValue('winsize', self.size())

if __name__ == "__main__":

    #  see if the ini file path was passed in
    if (len(sys.argv) > 1):
        iniFile = sys.argv[1]
        iniFile = os.path.normpath(iniFile)
    else:
        #  no argument provided, use default
        iniFile = 'clams.ini'

    #  create an instance of QSettings to load fundamental CLAMS settings
    print(iniFile)
    initSettings = QSettings(iniFile, QSettings.IniFormat)

    #  extract connection parameters
    dataSource = str(initSettings.value('ODBC_Data_Source', 'NULL').toString())
    user = str(initSettings.value('User', 'NULL').toString())
    password = str(initSettings.value('Password', 'NULL').toString())
    schema = str(initSettings.value('Schema', 'NULL').toString())

    #  create an instance of QApplication, our form, and then start
    app = QApplication(sys.argv)
    form = CLAMSCatchSummaryLoader(dataSource, schema, user, password)
    form.show()
    app.exec()
