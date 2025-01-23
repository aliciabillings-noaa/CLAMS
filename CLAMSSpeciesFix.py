
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6 import QtSql
from PyQt6.QtWidgets import *

from ui import  ui_CLAMSSpeciesFix
import numpad

import messagedlg


class CLAMSSpeciesFix(QDialog, ui_CLAMSSpeciesFix.Ui_clamsSpeciesFix):

    def __init__(self, parent=None):
        super(CLAMSSpeciesFix, self).__init__(parent)
        self.setupUi(self)
        #self.setAttribute(Qt.WA_DeleteOnClose)
        self.db=parent.db
        if not self.db.isOpen():
            self.db.open()
        self.workStation=parent.workStation
        self.survey=parent.survey
        self.ship=parent.ship
        self.activeHaul=parent.activeHaul
        self.activePartition=parent.activePartition
        self.settings=parent.settings
        self.errorSounds=parent.errorSounds
        self.errorIcons=parent.errorIcons
        self.backLogger=parent.backLogger
        #setup reoccuring dlgs
        self.numDialog = numpad.NumPad(self)
        self.message=messagedlg.MessageDlg(self)

        # figure out if this is administrative station
        actions = str(self.settings['MainActions'] )
        actions = actions.split(',')
        if 'Administration' in actions:
            self.admin=True
        else:
            self.admin=False


        # populate species window
        sql = ("SELECT species.common_name,species.scientific_name,samples.species_code," +
                "samples.sample_id,  samples.subcategory FROM species, samples, baskets "+
                "WHERE species.species_code = samples.species_code AND samples.ship = baskets.ship "+
                "AND samples.event_id = baskets.event_id AND samples.survey = baskets.survey "+
                "AND samples.sample_id = baskets.sample_id AND samples.ship = "+self.ship+" AND samples.survey="+
                self.survey+" AND samples.event_id="+self.activeHaul+" AND samples.partition='"+
                self.activePartition+"' AND baskets.basket_type='Measure' AND samples.species_code<>0 " +
                "GROUP BY species.common_name, samples.species_code, species.scientific_name, " +
                "samples.sample_id,  samples.subcategory",  self.db)
        query = self.db.dbQuery(sql)

        self.sampleDict={}
        self.oldSampleDict={}
        self.speciesCodes=[]
        self.selectionList = []
        for value in query:
            if value[4] != 'None':
                species_tag=value[0]+'-'+value[4]
            else:
                species_tag=value[0]

            self.newSpeciesBox.addItem(species_tag)
            self.sampleDict.update({species_tag:value[3]})


        # set up tables for data display
        font = QFont('helvetica', 14, -1, False)
        self.measureView.setFont(font)
        self.measureModel = QtSql.QSqlQueryModel()
        self.measureView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.measureView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.measureView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.measureView.setModel(self.measureModel)
        self.selModel = QItemSelectionModel(self.measureModel, self.measureView)
        self.measureView.setSelectionModel(self.selModel)
        self.measureView.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)

        self.measureView.show()

        # set up window position
        screen=QDesktopWidget().screenGeometry()
        window=self.geometry()
        self.setGeometry((screen.width()-window.width())/2,parent.windowAnchor[0]+(parent.windowAnchor[1]-window.height()), window.width(), window.height())
        self.setMinimumSize(window.width(), window.height())
        self.setMaximumSize(window.width(), window.height())

        # general slots
        self.doneBtn.clicked.connect(self.goExit)
        self.startIDBtn.clicked.connect(self.getIDRange)
        self.clearBtn.clicked.connect(self.clearFilters)
        self.endIDBtn.clicked.connect(self.getIDRange)
        self.applyChangeBtn.clicked.connect(self.applyChange)
        self.scientistBox.activated[int].connect(self.filterMeasurements)
        self.workstationBox.activated[int].connect(self.filterMeasurements)
        self.speciesBox.activated[int].connect(self.filterMeasurements)

        self.scientistBox.setCurrentIndex(-1)
        self.workstationBox.setCurrentIndex(-1)
        self.speciesBox.setCurrentIndex(-1)
        self.workstationBox.setEnabled(False)
        self.speciesBox.setEnabled(False)

        #  create a single-shot timer that runs the application initialization code
        #  this allows the application to complete the main window init method before
        #  the rest of the initialization code runs. We do this because we can't
        #  close the main window (as we would if there was an initialization error)
        #  from the window's init method.
        initTimer = QTimer(self)
        initTimer.setSingleShot(True)
        initTimer.timeout.connect(self.formInit)
        initTimer.start(0)

    def clearFilters(self):

        self.scientistBox.setCurrentIndex(-1)
        self.workstationBox.setCurrentIndex(-1)
        self.speciesBox.setCurrentIndex(-1)

        self.filterMeasurements()

        #self.populateFilters()
        #self.updateMeasureView()


    def formInit(self):

        QMessageBox.information(self, "Kipaumbele!", '<span style=" font-size:12pt;">This dialog ' +
                'allows you to reassign specimen that have been collected with an incorrect species or sex. ' +
                'This can happen (most likely at a length station) when someone forgets to change '+
                'the species or sex in CLAMS before moving onto different samples. To use it, ' +
                'specify the scientist, workstation, species, and range of specimen IDs that you ' +
                'would like to fix and select either the "Reassign Species" or the "Reassign Sex" ' +
                'tab. Then make the appropriate selection in that tab. Hit the "Apply Fix!" ' +
                'button to make the changes in the database.</span>')

        self.filterMeasurements()

    def applyChange(self):

        #  ensure that the sci-fi, workstation, and species are specified
        if (self.scientistBox.currentText() == '' or
            self.workstationBox.currentText() == '' or
            self.speciesBox.currentText() == ''):
            QMessageBox.warning(self, "Attention!", "You must specify the scientist, " +
                    "workstation, and species that are involed in this fix.")
            return
        #  ensure that we have a start ID
        if self.startIDLabel.text() == '':
            QMessageBox.warning(self, "Attenzione!", "You must specify the starting " +
                    "sample ID number.")
            return

        #  ensure we have an end ID
        if self.endIDLabel.text() == '':
            QMessageBox.warning(self, "Achtung!", "You must specify the ending " +
                    "sample ID number.")
            return

        #  get the selected tab and act accordingly
        selectedTab = str(self.reassignTabs.tabText(self.reassignTabs.currentIndex()))
        if selectedTab.lower() == 'reassign species':
            #  user has selcted species reassignment
            self.changeSpeciesAssignment()
        else:
            #  user has selcted sex reassignment
            self.changeSexAssignment()


    def getIDRange(self):
        # set active species

        if self.sender()==self.startIDBtn:
            self.numDialog.msgLabel.setText("Enter Start ID number")
            if not self.numDialog.exec_():
                return
            self.startIDLabel.setText(self.numDialog.value)
        else:
            self.numDialog.msgLabel.setText("Enter End ID number")
            if not self.numDialog.exec_():
                return
            self.endIDLabel.setText(self.numDialog.value)

    def filterMeasurements(self):
        self.filterString=''
        if self.sender()==self.scientistBox:
            self.filterString=" AND scientist = '"+self.scientistBox.currentText()+"' "
            self.workstationBox.setCurrentIndex(-1)
            self.workstationBox.setEnabled(True)
            self.speciesBox.setCurrentIndex(-1)
            self.speciesBox.setEnabled(False)

        elif self.sender()==self.workstationBox:
            self.filterString="AND scientist = '"+self.scientistBox.currentText()+"' AND workstation_id = "+self.workstationBox.currentText()+" "
            self.speciesBox.setCurrentIndex(-1)
            self.speciesBox.setEnabled(True)
        elif self.sender()==self.speciesBox:
            self.filterString="AND scientist = '"+self.scientistBox.currentText()+"' AND workstation_id = "+self.workstationBox.currentText()+" AND sample_id = "+self.oldSampleDict[self.speciesBox.currentText()]

        self.populateFilters()
        self.updateMeasureView()

    def populateFilters(self):
        if self.scientistBox.currentIndex() ==-1:
            self.scientistBox.clear()
            sql = ("SELECT scientist FROM V_SPECIMEN_MEASUREMENTS WHERE " +
                                " ship=" + self.ship +" AND survey=" + self.survey + " AND haul=" + self.activeHaul +
                                " AND partition='" + self.activePartition + "' "+self.filterString+" GROUP BY scientist ORDER BY scientist")
            query = self.db.dbQuery(sql)
            while query.next():
                self.scientistBox.addItem(query.value(0).toString())
            self.scientistBox.setCurrentIndex(-1)

        if self.workstationBox.currentIndex() ==-1:
            self.workstationBox.clear()
            sql = ("SELECT workstation_ID FROM V_SPECIMEN_MEASUREMENTS WHERE " +
                                " ship=" + self.ship +" AND survey=" + self.survey + " AND haul=" + self.activeHaul +
                                " AND partition='" + self.activePartition + "' "+self.filterString+" GROUP BY workstation_ID ORDER BY workstation_ID")
            query = self.db.dbQuery(sql)
            while query.next():
                self.workstationBox.addItem(query.value(0).toString())
            self.workstationBox.setCurrentIndex(-1)

        if self.speciesBox.currentIndex() ==-1:
            self.speciesBox.clear()
            sql = ("SELECT species_code, common_name, subcategory, sample_id FROM V_SPECIMEN_MEASUREMENTS WHERE " +
                                " ship=" + self.ship + " AND survey=" + self.survey + " AND haul=" + self.activeHaul +
                                " AND partition='" + self.activePartition + "' "+self.filterString+" GROUP BY species_code, common_name, subcategory, sample_id ORDER BY species_code")
            query = self.db.dbQuery(sql)
            while query.next():
                if query.value(2).toString() != 'None':
                    species_tag=query.value(1).toString()+'-'+query.value(2).toString()
                else:
                    species_tag=query.value(1).toString()

                self.speciesBox.addItem(species_tag)
                self.oldSampleDict.update({species_tag:query.value(3).toString()})
            self.speciesBox.setCurrentIndex(-1)

    def changeSpeciesAssignment(self):
        self.message.setMessage(self.errorIcons[1],self.errorSounds[1], "Are you sure you want to " +
                "change the species assignment for these fish?", 'choice')
        if self.message.exec_():
            try:
                newSampleKey=self.sampleDict[self.newSpeciesBox.currentText()]

                #  start a transaction so we can roll back if we run into problems
                self.db.transaction()

                #  disable the MEASUREMENT_SPECIMEN_FK constraint so we can modify the measurements and specimen tables
                #  without violating this constraint.
                sql = ("ALTER TABLE measurements DISABLE CONSTRAINT MEASUREMENT_SPECIMEN_FK;")
                query = self.db.dbQuery(sql)
                if (query.lastError().isValid()):
                    QMessageBox.critical(self, 'Error', 'Unable to change species assignment. Cannot disable constraint.')
                    self.db.rollback()
                    return

                for specimen_id in range(int(self.startIDLabel.text()), int(self.endIDLabel.text())+1):
                    sql = ("SELECT * FROM specimen WHERE specimen_id = "+ str(specimen_id)+
                            " AND ship=" + self.ship +" AND survey=" + self.survey + " AND event_id=" +
                            self.activeHaul+" AND workstation_id="+self.workstationBox.currentText())

                    query = self.db.dbQuery(sql)
                    if query.first():# valid chioce of specimen
                        sql = ("UPDATE specimen SET sample_id =" + newSampleKey+
                                " WHERE specimen_id = "+ str(specimen_id)+" AND ship=" + self.ship +
                                " AND survey=" + self.survey + " AND event_id=" + self.activeHaul+
                                " AND workstation_id="+self.workstationBox.currentText())

                        #  insert the last SQL statement into the local log file
                        query = self.db.dbQuery(sql)
                        self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss') + "," + query.lastQuery())


                        sql = ("UPDATE measurements SET sample_id =" + newSampleKey+
                                " WHERE specimen_id = "+ str(specimen_id)+" AND ship=" + self.ship +
                                " AND survey=" + self.survey + " AND event_id=" + self.activeHaul)
                        query = self.db.dbQuery(sql)
                        self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss') + "," + query.lastQuery())

                #  now re-enable the constraint with validation
                sql = ("ALTER TABLE measurements ENABLE CONSTRAINT MEASUREMENT_SPECIMEN_FK;")
                query = self.db.dbQuery(sql)
                if (query.lastError().isValid()):
                    #  there was a problem enabling the constraint - somehow the data is messed up - rollback
                    QMessageBox.critical(self, 'Error', 'Unable to change species assignment. ' +
                            'Changed data violated MEASUREMENT_SPECIMEN_FK. Database will be rolled back.')
                    self.db.rollback()

                    return
                else:
                    #  no problem enabling constraint - commit our changes
                    self.db.commit()
            except:
                QMessageBox.critical(self, 'Error', 'Unable to change species assignment')
                return

            #  update the view after making the changes
            self.updateMeasureView()

            #  and inform the user
            QMessageBox.information(self, 'Success!', 'Species assignment successfully changed.')

    def changeSexAssignment(self):
        self.message.setMessage(self.errorIcons[1],self.errorSounds[1], "Are you sure you want to change " +
                "the sex assignment for these fish?", 'choice')
        if self.message.exec_():
            try:

                #  get the new sex
                newSex = self.newSexBox.currentText()

                #  start a transaction so we can roll back if there is a problem
                self.db.transaction()

                #  disable the MEASUREMENT_SPECIMEN_FK constraint
                sql = ("ALTER TABLE measurements DISABLE CONSTRAINT MEASUREMENT_SPECIMEN_FK;")
                query = self.db.dbQuery(sql)
                if (query.lastError().isValid()):
                    QMessageBox.critical(self, 'Error', 'Unable to change sex assignment. Cannot disable constraint.')
                    self.db.rollback()
                    return

                #  work through the series of specimen identified by the start and end values
                for specimen_id in range(int(self.startIDLabel.text()), int(self.endIDLabel.text())+1):
                    #  filter the ID's by workstation
                    sql = ("SELECT specimen_id FROM specimen WHERE specimen_id = "+ str(specimen_id)+
                            " AND ship=" + self.ship +" AND survey=" + self.survey +  " AND event_id=" +
                            self.activeHaul+" AND workstation_id="+self.workstationBox.currentText())
                    query = self.db.dbQuery(sql)

                    if query.first():
                        #  this specimen is one that needs to change - change the sex to the specified value
                        sql = ("UPDATE measurements set measurement_value = '" +
                                newSex+"' where specimen_id = "+ str(specimen_id)+" AND ship=" +
                                self.ship +" AND survey=" + self.survey +" AND event_id=" + self.activeHaul +
                                " AND measurement_type = 'sex'")
                        #  insert the last SQL statement into the local log file
                        query1 = self.db.dbQuery(sql)
                        self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss') + "," + query1.lastQuery())


                #  attempt to enable the constraints
                sql = ("ALTER TABLE measurements ENABLE CONSTRAINT MEASUREMENT_SPECIMEN_FK;")
                query = self.db.dbQuery(sql)
                if (query.lastError().isValid()):
                    #  there was a problem enabling the constraint - somehow the data is messed up - rollback
                    QMessageBox.critical(self, 'Error', 'Unable to change sex assignment. ' +
                            'Changed data violated MEASUREMENT_SPECIMEN_FK. Database will be rolled back.')
                    self.db.rollback()
                    return
                else:
                    #  no problem enabling constraint - commit our changes
                    self.db.commit()
            except:
                QMessageBox.critical(self, 'Error', 'Unable to change sex assignment')
                return

            #  update the view after making the changes
            self.updateMeasureView()

            #  and inform the user
            QMessageBox.information(self, 'Success!', 'Sex assignment successfully changed.')


    def updateMeasureView(self):
        '''
        updateMeasureView updates the GUI table that presents the specimen measurements to the user.
        This method is called every time the specimen data changes. We take a very conservative approach
        where we requery the specimen data on every update to convince the user that the data is
        being recorded.
        '''
        self.sqlString='Scientist,Workstation_ID,Species_code, Sample_ID, fork_Length, Organism_weight, Sex '
        self.measureModel.setQuery("SELECT SPECIMEN_ID, "+ self.sqlString+" FROM V_SPECIMEN_MEASUREMENTS WHERE " +
                            " ship=" + self.ship +" AND survey=" + self.survey + " AND haul=" + self.activeHaul +
                            " AND partition='" + self.activePartition + "' "+self.filterString+" ORDER BY SPECIMEN_ID")

        self.measureModel.reset()
        self.measureView.scrollToBottom()



    def goExit(self):
        self.close()

    def closeEvent(self, event):
        event.accept()



