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
.. module:: CLAMScatch

    :synopsis: CLAMScatch presents the CLAMS catch form. The catch form
               is used to specify what was caught in the catch, as well
               as if/how it will be further processed. The catch module
               is used when the catch is sorted and weighed.

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

#  imports
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from ui import ui_CLAMSCatch
import addcatchspcdlg
import numpad
import typeseldialog
import basketeditdlg
import keypad
import transferdlg
import messagedlg
import ZebraLabelPrinter
import addspecdlg


class CLAMSCatch(QDialog, ui_CLAMSCatch.Ui_clamsCatch):

    def __init__(self, parent=None):

        #  call superclass init methods and GUI form setup method
        super(CLAMSCatch, self).__init__(parent)
        self.setupUi(self)

        #  copy some info from parent for convenience
        self.db = parent.db
        self.serMonitor = parent.serMonitor
        self.workStation = parent.workStation
        self.activeHaul = parent.activeHaul
        self.survey = parent.survey
        self.ship = parent.ship
        self.settings = parent.settings
        self.activePartition = parent.activePartition
        self.errorSounds = parent.errorSounds
        self.errorIcons = parent.errorIcons
        self.scientist = parent.scientist

        # initialize variables
        self.addspec_flag = True
        self.planktonFlag = False
        self.activeSampleKey = None
        self.activeSpcName = None
        self.activeSpcCode = None
        self.comment = ''
        self.validList = [1, 1, 1]# sets valid sample type choices
        self.freeze = False
        self.whHaulFlag = False
        self.devices = []
        self.sounds = {}
        self.basketTypes = []
        self.manualDevice ='0'
        self.parentSamples = {}
        self.mixtureNames = {'100000':'WholeHaul', '100001':'SortingTable',
                '100002':'Mix1', '100003':'SubMix1', '100004':'Mix2'}
        self.wholeHaulKey=None

        #  do some UI setup
        self.sciLabel.setText(self.scientist)
        self.firstName = self.scientist.split(' ')[0]

        #  set up tables for data display
        font = QFont("Arial Black", 14, -1, False)
        self.basketView.setFont(font)
        self.basketModel = QtSql.QSqlQueryModel()
        self.basketView.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.basketView.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.basketView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.basketView.setModel(self.basketModel)
        self.selModel = QItemSelectionModel(self.basketModel, self.basketView)
        self.basketView.setSelectionModel(self.selModel)
        self.basketView.horizontalHeader().setResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.basketView.show()

        self.sumTable.setColumnWidth(0, 100)
        self.sumTable.setColumnWidth(1, 100)

        # set up recurring dialogs
        self.message = messagedlg.MessageDlg(self)
        self.numpad = numpad.NumPad(self)
        self.addspec = addspecdlg.addspecedlg(self)
        self.typeDlg = typeseldialog.TypeSelDialog(self)
        self.spcDlg = addcatchspcdlg.AddCatchSpcDlg(self)

        #  connect signals and slots
        self.addspcBtn.clicked.connect(self.getSpecies)
        self.manualBtn.clicked.connect(self.getManual)
        self.doneBtn.clicked.connect(self.close)
        self.delBtn.clicked.connect(self.goDelete)
        self.printBtn.clicked.connect(self.printLabel)
        self.editBtn.clicked.connect(self.editTable)
        self.speciesList.itemSelectionChanged.connect(self.getActiveSpc)
        self.speciesList.itemActivated.connect(self.getSpeciesFocus)
        self.selModel.selectionChanged[QItemSelection,QItemSelection].connect(self.getBasketRow)
        self.transBtn.clicked.connect(self.transferSample)
        self.commentBtn.clicked.connect(self.getComment)
        self.spcDlg.changed.connect(self.addSpecies)

        #  connect the SensorMonitor SerialDataReceived signal to the
        #  getAuto method which processes input from devices.
        self.serMonitor.SerialDataReceived.connect(self.getAuto)

        #  restore the application state
        self.appSettings = QSettings('CLAMS', 'CatchForm')
        size = self.appSettings.value('winsize', QSize(950,665))
        position = self.appSettings.value('winposition', QPoint(10,10))

        #  check the current position and size to make sure the app is on the screen
        position, size = self.checkWindowLocation(position, size)

        #  now move and resize the window
        self.move(position)
        self.resize(size)

        #  create a timer to complete init after initial form presentation
        checkHaulTimer = QTimer(self)
        checkHaulTimer.setSingleShot(True)
        checkHaulTimer.timeout.connect(self.formInit)
        checkHaulTimer.start(0)


    def formInit(self):
        '''formInit is called immediately after the form is presented on
        screen and it continues form/module setup. It checks to make sure we
        have completed the haul form for this partition and inserts/updates
        some base samples table entries

        '''

        #  First, check to see if haul form has been checked for codend partition
        if 'codend' in self.activePartition.lower():
            sql = ("SELECT parameter_value FROM event_data WHERE ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+self.activeHaul+
                " AND partition='" + self.activePartition +
                "' AND event_parameter='PartitionWeightType'")

            query = self.db.dbQuery(sql)
            pwt, = query.first()
            if not pwt:
                #  there isn't a partition weight type for this partition so
                #  we can't go on.
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                        "You need to visit haul form before you can enter codend catch.",'info')
                self.message.exec()
                self.close()
                return



        # get sample types
        sql = ("SELECT gear_options.basket_type FROM gear_options INNER JOIN " +
                "events ON gear_options.gear=events.gear WHERE events.ship=" + self.ship+
                " AND events.survey=" + self.survey + " AND events.event_id=" + self.activeHaul+
                " AND gear_options.basket_type is not NULL ORDER BY gear_options.basket_type")
        query = self.db.dbQuery(sql)
        for basketType, in query.next():
            self.basketTypes.append(basketType)

        #  check if this is a plankton trawl  - they're handled a bit differently
        sql = ("SELECT GEAR.GEAR_TYPE FROM events, GEAR WHERE (events.GEAR = "+
                "GEAR.GEAR ) and  ((events.SHIP = "+self.ship+" ) AND (events.SURVEY = "+
                self.survey+" ) AND (events.event_id = "+self.activeHaul+"))")
        query = self.db.dbQuery(sql)
        gearType, = query.first()
        if gearType == 'PlanktonNet':
            self.planktonFlag = True


        #  Check if we have a label printer attached at this workstation. If so,
        #  create the printer object and if not, disable the print button
        sql = ("SELECT MEASUREMENT_SETUP.DEVICE_ID, DEVICES.DEVICE_NAME " +
                "FROM MEASUREMENT_SETUP INNER JOIN DEVICES ON " +
                "MEASUREMENT_SETUP.DEVICE_ID = DEVICES.DEVICE_ID WHERE " +
                "MEASUREMENT_SETUP.WORKSTATION_ID = " +  self.workStation +
                " AND DEVICES.DEVICE_NAME = 'Label_Printer'" +
                " GROUP BY MEASUREMENT_SETUP.DEVICE_ID, DEVICES.DEVICE_NAME")
        query = self.db.dbQuery(sql)
        printerId, printerName = query.first()
        if printerId:
            #  initialize the Label Printer
            self.printer = ZebraLabelPrinter.ZebraLabelPrinter(self.serMonitor, printerName)
        else:
            #  no printer configured
            self.printer = None
            self.printBtn.setEnabled(False)

        #  set up the printer sound.
        sql = ("select a.parameter_value from device_configuration a," +
                "devices b where a.device_id=b.device_id " +
                "and b.device_name='Label_Printer' and a.device_parameter='SoundFile'")
        query = self.db.dbQuery(sql)
        soundFile, = query.first()
        if soundFile:
            hasExt = soundFile.split('.')
            if len(hasExt) > 1:
                soundFile = self.settings['SoundsDir'] + soundFile
            else:
                soundFile = self.settings['SoundsDir'] + soundFile + '.wav'
            soundEffect = QSoundEffect()
            soundEffect.setSource(QUrl.fromLocalFile(soundFile))
            self.printSound = soundEffect
        else:
            self.printSound = None



        #  setup parent sample. if not present, create whole catch sample which is
        #  the top level sample (no parent)
        sql = ("SELECT sample_id FROM samples WHERE ship="+self.ship+" AND survey="+
                self.survey+" AND event_id="+self.activeHaul+" AND partition ='"+self.activePartition+
                "' AND species_code=100001")
        query = self.db.dbQuery(sql)
        sampleID, = query.first()
        if not sampleID:
            #  the parent sample doesn't exist yet, so create it.
            sql = ("INSERT INTO samples (ship, survey, event_id, partition, " +
                    "sample_type,species_code, scientist) VALUES("+self.ship+","+self.survey+
                    ","+self.activeHaul+ ",'"+self.activePartition+"','SortingTable',100001,'"
                    +self.scientist+"')")
            self.db.dbExec(sql)

            #  now retrieve newly created sample ID from database
            sql = ("SELECT sample_id FROM samples WHERE ship="+self.ship+
                    " AND survey="+self.survey+" AND event_id="+self.activeHaul+
                    " AND partition ='"+self.activePartition+"' AND species_code=100001")
            query = self.db.dbQuery(sql)
            sampleID, = query.first()

        self.sortingTableKey = sampleID

        # is this a splitter?  if so create whole haul parent key
        sql = ("SELECT event_data.PARAMETER_VALUE FROM event_data  WHERE " +
                "(event_data.SHIP="+self.ship+") AND (event_data.SURVEY="+self.survey+
                ") AND (event_data.event_id="+self.activeHaul+") AND "+
                "(event_data.PARTITION='"+self.activePartition+"') AND "+
                "(event_data.event_parameter='PartitionWeightType')")

        query = self.db.dbQuery(sql)
        partitionWeightType, = query.first()

        if partitionWeightType:
            if partitionWeightType.lower() != 'not_subsampled':
                #  this is a splitter - check if we have the whole haul
                #  sample and if not, create it.
                sql = ("SELECT sample_id FROM samples WHERE ship="+self.ship+
                        " AND survey="+self.survey+" AND event_id="+self.activeHaul+
                        " AND partition ='"+self.activePartition+"' AND species_code=100000")
                query = self.db.dbQuery(sql)
                wholeHaulID, = query.first()

                if not wholeHaulID:
                    #  we don't already have this sample id- first catch has been run
                    #  for this event.
                    sql = ("INSERT INTO samples (ship, survey, event_id, partition, " +
                            " sample_type, species_code,scientist) VALUES("+self.ship+","+self.survey+
                            ","+self.activeHaul+",'"+self.activePartition+"'"+
                            ",'WholeHaul',100000, '"+self.scientist+"')")
                    self.db.dbExec(sql)

                    # retrieve newly created sample key from database
                    sql = ("SELECT sample_id FROM samples WHERE ship="+self.ship+
                            " AND survey="+self.survey+" AND event_id="+self.activeHaul+
                            " AND partition ='"+self.activePartition+"' AND species_code=100000")

                    query = self.db.dbQuery(sql)
                    wholeHaulID, = query.first()

                self.wholeHaulKey = wholeHaulID

                # update parent key for 'sorting table' sample
                sql = ("UPDATE samples SET parent_sample="+self.wholeHaulKey+" WHERE ship="+self.ship+
                    " AND survey="+self.survey+" AND event_id="+self.activeHaul+
                    " AND partition ='"+self.activePartition+"' AND species_code=100001")
                self.db.dbExec(sql)

                # set the wholeHaul flag since this is a splitter
                self.whHaulFlag=True
            else:
                #  catch not subsampled - unset wholeHaul flag
                self.whHaulFlag=False
        else:
            #  If we don't have a partition weight type, then we're not subsampling
            self.whHaulFlag=False

        # set up device sounds
        self.loadDeviceSounds()

        #  reload the species list - this populates the species list
        self.reloadSpeciesList()


        self.updateParentKeys()


    def getSpecies(self):
        '''getSpecies is called when the Add Species button is pressed and it pauses
        device input and displays the add species dialog.
        '''
        #  set freeze to ignore sensor/device input while adding species
        self.freeze=True

        #  show the add species dialog
        self.spcDlg.exec()

        #  unset freeze to continue processing sensor/device input
        self.freeze=False


    def addSpecies(self):
        '''addSpecies is called when a species is added using the add species dialog.

        '''
        self.addspec_flag = False

        code = self.spcDlg.activeSpcCode
        spcName = self.spcDlg.activeSpcName
        subCat = self.spcDlg.activeSpcSubcat

        # parent sample
        parentKey  = self.parentSamples[self.spcDlg.parentSample]
        self.createSample(code, spcName, subCat,  self.spcDlg.nameType,  parentKey)

        #
        self.updateParentKeys()

        # are we creating a mix sample? Need the parent key for species in mix...

        # make this new addition the active one...
        self.reloadSpeciesList()

        self.addspec_flag = True


    def updateParentKeys(self):

        #  check if we have a mix
        for code in ['100002', '100003', '100004']:
            sql = ("SELECT species.common_name, samples.sample_id  " +
                    "FROM samples, species WHERE species.species_code=samples.species_code " +
                    "AND samples.species_code =" + code + " AND samples.ship=" + self.ship +
                    " AND samples.survey=" + self.survey + " AND samples.event_id=" +
                    self.activeHaul + " AND samples.partition='" + self.activePartition + "'")
            query = self.db.dbQuery(sql)
            common_name, sample_id = query.first()

            if common_name:
                #  yes, we have a mix
                spcName = common_name
                parentKey = sample_id
                if not parentKey in self.parentSamples:
                    self.parentSamples.update({spcName:parentKey})

        if not self.wholeHaulKey in self.parentSamples:
            self.parentSamples.update({QString('WholeHaul'):self.wholeHaulKey})
        if not self.sortingTableKey in self.parentSamples:
            self.parentSamples.update({QString('SortingTable'):self.sortingTableKey})


    def createSample(self, code, name, subCat, nameType, parentSample):

        #  check if the species that we're being told to add is already in
        #  out list of samples.
        if subCat != 'None':
            if self.speciesList.findItems(name+"-"+subCat, Qt.MatchFlag.MatchExactly):
                #  species + subcat is already in the list - just return
                return
        else:
            if self.speciesList.findItems(name, Qt.MatchFlag.MatchExactly):
                #  species is already in the list - just return
                return

        #  set the sample type - first, check if we're adding a mix
        if code in ('100002', '100003', '100004'):
            #  this is a mix type
            sampleType = self.mixtureNames[code]
        else:
            #  this is not a mix, so assume this is a Species sample type
            sampleType='Species'

        #  insert this data into the samples table
        sql = ("INSERT INTO samples (ship,survey,event_id,partition,sample_type," +
                "species_code,subcategory,parent_sample,scientist) VALUES("+
                self.ship+","+self.survey+","+ self.activeHaul+",'"+self.activePartition+
                "','"+sampleType+"',"+code+",'"+subCat+"',"+parentSample+",'"+
                self.scientist+"')")
        self.db.dbExec(sql)

        #  get the new sample ID for the just inserted sample
        sql = ("SELECT max(sample_id) FROM samples WHERE ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+ self.activeHaul+
                " AND partition ='"+self.activePartition+"'")
        query = self.db.dbQuery(sql)
        sample_id, = query.first()


        #  insert the sample_display_name param in the sample_data table. This
        #  informs CLAMS as to which name (sci or common) to display in the UI
        #  for this sample.
        sql = ("INSERT INTO sample_data (ship,survey,event_id,sample_id,sample_parameter,"
                "parameter_value) VALUES("+self.ship+","+self.survey+","+
                self.activeHaul+","+sample_id+",'sample_display_name','"+nameType+"')")
        self.db.dbExec(sql)


    def setActiveSpecies(self, spc_name, subcat):

        # this is for programattically setting active species

        if subcat=='None':
            spc_tag=spc_name
        else:
            spc_tag=spc_name+"_"+subcat

        self.speciesList.setCurrentItem(spc_tag, Qt.MatchFlag.MatchExactly)
        self.activeSpcSubcat = subcat
        self.activeSpcName = spc_name
        self.activeSampleKey = self.speciesList.verticalHeaderItem(self.speciesList.currentRow()).text()
        self.activeSpcCode = self.speciesDict[self.activeSpcName]

        # look for previous data on species
        self.updateTables()
        self.focus='speciesList'

        #  load the spp image
        self.loadSppImage()

        #  check if user has selected a mix
        if self.speciesList.item(self.speciesList.currentRow(), 1).text() == 'mix1':
            self.inMixFlag = True
        else:
            self.inMixFlag = False

        #  load this sample's comments
        sql = ("SELECT comments FROM samples WHERE (ship=" + self.ship +
                " and survey=" + self.survey + " and event_id=" + self.activeHaul +
                " and sample_id=" +self.activeSampleKey + ")")
        query = self.db.dbQuery(sql)
        sampleComments, = query.first()
        if sampleComments:
            self.comment = sampleComments


    def checkSampleExists(self, sampID):
        '''
        checkSampleExists checks if the sample ID is still present in the database. Returns
        True if so, and False if not.
        '''
        sql = ("SELECT sample_id from samples WHERE ship=" + self.ship +
                " AND survey=" + self.survey + " AND event_id=" + self.activeHaul+
                " AND sample_id=" + sampID)
        query = self.db.dbQuery(sql)
        sampleID, = query.first()
        if sampleID:
            return True
        else:
            return False


    def loadSppImage(self):
        '''loadSppImage loads the active species image in GUI form and is called
        when the species selection changes.
        '''

        # set up picture
        if self.activeSpcSubcat.lower() != 'none':
            imgName = self.activeSpcCode+"_"+self.activeSpcSubcat
        else:
            imgName = self.activeSpcCode

        #  currently, all fish images must be .jpg.
        imgName = imgName + ".jpg"

        #  load the fish pic, if available
        self.picLabel.clear()
        pic = QImage()
        if pic.load(self.settings['ImageDir'] + 'fishPics' + os.sep + imgName):
            pic = pic.scaled(self.picLabel.size(),Qt.AspectRatioMode.KeepAspectRatio)
            self.picLabel.setPixmap(QPixmap.fromImage(pic))
            self.picLabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.picLabel.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        else:
            #  no pic available
            self.picLabel.clear()
            self.picLanel.setText("<Image Unavailable>")


    def getActiveSpc(self):
        '''getActiveSpc is called when the user selects a species from the species list.

        '''
        self.basketView.setEnabled(True)
        self.sumTable.setEnabled(True)

        # default setting for a species is no whole haul

        #  This method will also be triggered when a species is deleted so
        #  we need check if there are any species left and if not, bail since
        #  there are no spp to set active.
        if self.speciesList.currentRow() < 0:
            #  nothing in the list
            return

        #  get the species text
        text = self.speciesList.item(self.speciesList.currentRow(), 0).text()

        #  check to make sure this sample still exists - stations can get out of sync with the samples
        #  list if someone deletes a sample at a different station after someone opens this form.
        sampID = self.speciesList.verticalHeaderItem(self.speciesList.currentRow()).text()
        ok = self.checkSampleExists(sampID)

        #  check if the sample ID is still present in the database. It could have been
        #  deleted by a different user
        sql = ("SELECT sample_id from samples WHERE ship=" + self.ship +
                " AND survey=" + self.survey + " AND event_id=" + self.activeHaul+
                " AND sample_id=" + sampID)
        query = self.db.dbQuery(sql)
        sampleID, = query.first()
        if not sampleID:
            #  this sample has been deleted - inform the user and remove from the list
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                        "The sample you selected has been deleted by someone else. " +
                        "You must re-add it if you need it.",'info')
            self.message.exec()
            #  refresh the species list
            self.reloadSpeciesList()
            return

        #  display the dialog for confirming active species - this was introduced
        #  after it was discovered that if you select one item, then roll your
        #  finger to a different item, the first item appears visually to be
        #  selected but the second item is the one that is identified by
        #  self.speciesList.currentRow() resulting in confusion. This dialog
        #  confirms the user's selection and brings to attention any discrepancy
        #  if the select and roll happens.
        if self.addspec_flag == True:
            self.freeze = True
            self.addspec.setMessage(self.errorIcons[1], self.errorSounds[2],
                    "Changing the Active Species to: \n \n"+ text ,'info')
            self.addspec.exec()
            self.freeze = False

        #  check if this species has a subcategory and adjust the name
        text1 = text.split('-')
        if len(text1) > 1:
            self.activeSpcSubcat = text1[-1]
            self.activeSpcName='-'.join(text1[0:-1])
        else:
            self.activeSpcSubcat = 'None'
            self.activeSpcName = text1[0]

        self.activeSampleKey=self.speciesList.verticalHeaderItem(self.speciesList.currentRow()).text()
        self.activeSpcCode=self.speciesDict[str(self.activeSpcName)]

        # look for previous data on species
        self.updateTables()
        self.focus='speciesList'

        #  load the spp image
        self.loadSppImage()

        if self.speciesList.item(self.speciesList.currentRow(), 1).text() == 'mix1':
            self.inMixFlag=True
        else:
            self.inMixFlag=False

        sql = ("SELECT comments FROM samples WHERE (ship=" + self.ship +
                " and survey=" + self.survey + " and event_id=" +self.activeHaul +
                " and sample_id=" + self.activeSampleKey + ")")
        query = self.db.dbQuery(sql)
        sampleComments, = query.first()
        if sampleComments:
            self.comment = sampleComments


    def getManual(self):
        '''getManual is called when the user clicks the manual weight button. It
        makes sure a species sample is selected and presents a dialog to enter
        the weight.
        '''
        # is a species selected
        if self.activeSpcName is None:
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2], self.firstName +
                    ", please select a species.",'info')
            self.message.exec()
            return

        self.numpad.msgLabel.setText("Enter the Weight")
        if not self.numpad.exec():
            return

        #  check that we didn't get a 0 weight
        if (self.numpad.value == 0):
            self.message.setMessage(self.errorIcons[2],self.errorSounds[2],
                    "You have entered 0 (zero) for the basket weight which is not " +
                    "allowed. If your sample is too small to register " +
                    "on the scale, you should enter 0.001", 'info')
            self.message.exec()
            return

        #  get the manual weight using the numpad dialog
        self.currentBasketWt = self.numpad.value

        #  note that this is a manual entry
        self.manualFlag = True
        self.device = self.manualDevice

        #  do some basic checks, get the basket type, then insert into the database
        self.updateBasket()


    def getAuto(self, device, val):
        '''getAuto is called when a device sends data

        '''
        #  check if we're "frozen" which means either adding spp or in the middle of
        #  weighing another basket
        if self.freeze:
            return

        #  check if this is a device we're interested in, if not, ignore this data. For
        #  example, this station could have a lengtboard, but the catch module only cares
        #  about scales so we ignore data from the lengthboard.
        if not device in self.devices:
            return

        # check if a species is selected
        if self.activeSpcName == None:
            self.message.setMessage(self.errorIcons[2],self.errorSounds[2], self.firstName +
                    ", please select a species.",'info')
            self.message.exec()
            return

        #  ensure that the value is numeric - noise on the data lines, poor connections,
        #  or bad power can result in garbled data.
        try:
            val = float(val)
        except:
            self.message.setMessage(self.errorIcons[2],self.errorSounds[2],
                    "The scale sent a non-numeric value!?! Please try again.", 'info')
            self.message.exec()
            return

        #  check that we didn't get a 0 weight
        if (val <= 0):
            self.message.setMessage(self.errorIcons[2],self.errorSounds[2],
                    "The scale sent a weight of 0 (zero) which is not allowed. " +
                    "If your sample is too small to register " +
                    "on the scale, you should manually enter 0.001", 'info')
            self.message.exec()
            return

        #  set the basket value
        self.currentBasketWt = val

        #  note that this is an "auto" (non manual) entry
        self.manualFlag = False
        self.device = device

        #  play the scale sound
        self.sounds[self.devices.index(self.device)].play()

        #  do some basic checks, get the basket type, then insert into the database
        self.updateBasket()


    def getWeightValidation(self):
        '''getWeightValidation performs some basic validations on the
        basket weight measurement.

        '''
        #  check basket weight against the max allowed basket weight
        if float(self.currentBasketWt) > float(self.settings[QString('MaxBasketWt')]):
            self.message.setMessage(self.errorIcons[1],self.errorSounds[1], self.firstName +
                    ", this Basket exceeds the maximum basket weight of " +
                    self.settings['MaxBasketWt']+".  Does this bother you?", 'choice')
            if self.message.exec():
                #  user has rejected the measurement
                return False

        #  if this is a mix, check for mix subsample weight and stuff
        if self.inMixFlag:
            #  yes, this is a mix
            (mixSubWeight, mixSpeciesWeight) = self.mixValidation()

            # validation for mix sub weight - can't have more weight in sub part of mix than in mix subsample
            if (mixSubWeight * (1 + float(self.settings['MaxMixDev']) / 100) <
                    (mixSpeciesWeight + float(self.currentBasketWt))):
                self.message.setMessage(self.errorIcons[0],self.errorSounds[0],
                        self.firstName + ", it appears that the total weight of species" +
                        " in the mix exceeds the mix subsample by more than " +
                        self.settings['MaxMixDev']+" % - this is usually bad. " +
                        "Do you want to fix this now?",'info')
                if self.message.exec():
                    #  user has rejected the measurement
                    return False

        #  weight passes basic validation
        return True



    def getBasketType(self):
        '''getBasketType is called after a basket weight is collected and
        presents the user with the basket type dialog where they choose if
        the basket is a measure, count, or toss basket.

        '''

        #  first, if we're in a mix, disable the count button
        if self.activeSpcCode in ['100002', '100003', '100004']:
            self.validList[self.basketTypes.index('Count')] = 0
        else:
            self.validList[self.basketTypes.index('Count')] = 1

        #  display the basket type dialog
        self.typeDlg.buttonSetup(self.validList)
        if self.typeDlg.exec():
            self.basketType = self.typeDlg.basketType
            self.count=self.typeDlg.count
        else:
            self.message.setMessage(self.errorIcons[2],self.errorSounds[2],
                    "You didn't choose a Basket type, you bugger",'info')
            self.message.exec()
            self.basketType = None


    def updateBasket(self):
        '''updateBasket is called after the user sends a weight with the scale
        or enters the weight manually. It performs basic validation, gets the basket
        type, and then inserts the data into the database.

        '''

        #  set the "freeze" flag so we ignore input from the scale while we're finishing this basket
        self.freeze = True

        #  run the weight validation
        ok = self.getWeightValidation()
        if not ok:
            #  this weight is not valid
            self.freeze = False
            return

        #  get the sample type
        self.getBasketType()
        if self.basketType == None:
            #  user cancelled sample type selection
            self.freeze = False
            return

        #  write basket record for this basket
        if self.count == None:
            sql = ("INSERT INTO baskets (ship,survey,event_id,sample_id,basket_type," +
                    "weight, device_id) VALUES ("+ self.ship+", "+self.survey+","+
                    self.activeHaul+","+self.activeSampleKey+",'"+self.basketType+"',"
                    +self.currentBasketWt+","+self.device+")")
        else:
            sql = ("INSERT INTO baskets (ship,survey,event_id,sample_id,basket_type,count," +
                    "weight,device_id) VALUES ("+ self.ship+", "+self.survey+","+self.activeHaul +
                    ","+self.activeSampleKey+",'"+self.basketType+"',"+self.count+"," +
                    self.currentBasketWt+","+self.device+")")
        self.db.dbExec(sql)

        # update the GUI
        self.updateTables()

        #  we're done with this basket - unfreeze
        self.freeze = False


    def updateTables(self):


        #  update the basket
        self.basketModel.setQuery("SELECT basket_id, weight, count,basket_type " +
                "FROM baskets WHERE ship="+self.ship+" AND survey="+self.survey+
                " AND event_id="+self.activeHaul+" AND sample_id ="+
                self.activeSampleKey+" ORDER BY basket_id", self.db)
        self.basketModel.reset()
        self.basketView.scrollToBottom()
        self.basketView.resizeColumnsToContents()
        self.updateSumTable()


        self.sumTable.clearContents()
        self.sumTable.setRowCount(0)
        for i in range(3):
            self.sumTable.setVerticalHeaderItem(i, QTableWidgetItem(""))
        # get counts per basket type
        query=QtSql.QSqlQuery("SELECT sum(WEIGHT), count(weight), basket_type FROM BASKETS "+
        " WHERE ship="+self.ship+" AND survey="+self.survey+" AND event_id="+self.activeHaul+" AND sample_id="+self.activeSampleKey+" GROUP BY basket_type")
        cnt=0
        totWt=0
        totCnt=0
        while query.next():
            self.sumTable.insertRow(cnt)
            self.sumTable.setVerticalHeaderItem(cnt,QTableWidgetItem(query.value(2).toString()))
            self.sumTable.setItem(cnt, 0, QTableWidgetItem(query.value(0).toString()))
            self.sumTable.setItem(cnt, 1, QTableWidgetItem(query.value(1).toString()))
            cnt+=1
            totWt=totWt+float(query.value(0).toString())
            totCnt=totCnt+float(query.value(1).toString())
        # get total
        self.sumTable.insertRow(cnt)
        self.sumTable.setVerticalHeaderItem(cnt,QTableWidgetItem('Total'))
        self.sumTable.setItem(cnt, 0, QTableWidgetItem(str(totWt)))
        self.sumTable.setItem(cnt, 1, QTableWidgetItem(str(totCnt)))
        self.sumTable.resizeColumnsToContents()


    def getSpeciesFocus(self):
        self.focus='speciesList'


    def getBasketRow(self):
        self.focus='basketList'
        self.selRecord=[]
        selObj=self.basketView.currentIndex()
        for i in range(4):
            index= self.basketModel.index(selObj.row(), i, QModelIndex())
            self.selRecord.append(self.basketModel.data(index, Qt.DisplayRole).toString())


    def deleteSpecimen(self):
        """
        deleteSpecimen is called when the user wants to delete a basket or sample and
        specimen exist in the database.
        """

        #  double check that they want to delete the specimen
        self.message.setMessage(self.errorIcons[3],self.errorSounds[1],
                "Are you REALLY sure you want to delete these specimen?", 'choice')
        if self.message.exec_():
            #  they want to do it - delete the measurements
            query=QtSql.QSqlQuery("DELETE FROM measurements WHERE ship=" + self.ship +
                    " AND survey = " + self.survey + " AND event_id=" + self.activeHaul +
                    " AND sample_id ="+ self.activeSampleKey)
            self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

            #  delete the specimen records
            query=QtSql.QSqlQuery("DELETE FROM specimen WHERE ship=" + self.ship +
                    " AND survey = " +self.survey + " AND event_id=" + self.activeHaul +
                    " AND sample_id ="+self.activeSampleKey)
            self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

            #  try to delete from the catch summary and length histogram tables - these will be
            #  populated at this point if a user has come back into CLAMS to edit a past haul
            query=QtSql.QSqlQuery("DELETE FROM catch_summary WHERE ship=" + self.ship +
                    " AND survey = " +self.survey + " AND event_id=" + self.activeHaul +
                    " AND sample_id ="+self.activeSampleKey)
            self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())
            query=QtSql.QSqlQuery("DELETE FROM length_histogram WHERE ship=" + self.ship +
                    " AND survey = " +self.survey + " AND event_id=" + self.activeHaul +
                    " AND sample_id ="+self.activeSampleKey)
            self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

            #  set the return value to true since we deleted the specimen
            deleted = True

        else:
            #  user changed their mind
            deleted = False

        return deleted


    def goDelete(self):
        """
        goDelete  deletes either baskets or a sample depending on what widget has focus
        (basket list or sample list)
        """

        if self.activeSampleKey==None:
            return

        hasSpecimen=False
        nOther = 0
        nMeasure = 0

        #  first check if we have specimen - this process a bit more complicated with specimen
        query=QtSql.QSqlQuery("SELECT specimen_id FROM specimen WHERE ship="+self.ship+" AND survey="+
                self.survey+" AND event_id="+self.activeHaul+" AND sample_id ="+self.activeSampleKey)
        if query.first():
            # the active species has specimen data
            hasSpecimen=True

        #  determine type and count of baskets for this sample. We need to know this because if
        #  the user is trying to delete the last "measure" basket and there are samples, the
        #  samples have to be deleted too.
        query=QtSql.QSqlQuery("SELECT basket_type FROM baskets WHERE ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+self.activeHaul+" AND sample_id = "
                +self.activeSampleKey)
        while query.next():
            if query.value(0).toString() == 'Measure':
                #  this is a measure basket
                nMeasure = nMeasure + 1
            else:
                #  this is a count, preserve, or toss basket
                nOther = nOther + 1

        #  now move ahead based on where the focus is in the GUI. If a basket is selected, we
        #  attempt to delete that single basket. If a sample is selected, we attempt to delete the
        #  whole sample.

        #  if the focus is on the basket list, delete the selected basket
        if self.focus=='basketList':

            #  if there is only 1 measure basket left and there are specimen, check if the selected
            #  basket is that lone measure basket
            if nMeasure == 1 and hasSpecimen:
                query=QtSql.QSqlQuery("SELECT basket_type FROM baskets WHERE ship="+self.ship+
                        " AND survey="+self.survey+" AND event_id="+self.activeHaul+" AND basket_id="+
                        self.selRecord[0])
                if query.value(0).toString() == 'Measure':
                    #  this is the last measure basket and specimen exist
                    self.message.setMessage(self.errorIcons[1],self.errorSounds[1],
                            "This is the last basket of type 'Measure' for this species and specimen " +
                            "exist for this species. If you delete this basket, the specimen will be " +
                            "deleted as well. Are you SURE you want to permanently delete this basket " +
                            "AND all of the specimen collected for this species, "+
                            self.firstName+"?", 'choice')
                    if self.message.exec_():
                        #  user chose to delete the specimen (we'll ask one more time)
                        ok = self.deleteSpecimen()

                        if not ok:
                            #  user changed their mind when we asked if they're sure - we're done here
                            return
                    else:
                        #  user changed their mind - we're done here
                        return

                #  Either this basket wasn't a measure type or it was and we deleted all of the
                #  associated specimen. Now we delete the basket
                query =QtSql.QSqlQuery("DELETE FROM baskets WHERE ship="+self.ship+" AND survey="+
                            self.survey+" AND event_id="+self.activeHaul+" AND basket_id="+
                            self.selRecord[0], self.db)
                self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+
                        query.lastQuery())

            else:
                #  this is not the last measure basket so we just delete the basket regardless of
                #  type and assume the user knows what they are doing

                self.message.setMessage(self.errorIcons[3],self.errorSounds[1], "Are you sure you want " +
                        "to permanently delete this basket, "+self.firstName+"?", 'choice')
                if self.message.exec_():
                    #  user chose to delete
                    query =QtSql.QSqlQuery("DELETE FROM baskets WHERE ship="+self.ship+" AND survey="+
                            self.survey+" AND event_id="+self.activeHaul+" AND basket_id="+
                            self.selRecord[0], self.db)
                    self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+
                            query.lastQuery())

        #  if the focus is on the sample list so we're going to delete the entire sample
        elif self.focus=='speciesList':

            #  make sure the user really wants to do the
            if hasSpecimen:
                #  if there are specimen associated with this sample, we present a different dialog
                #  and then have to first delete the specimen
                self.message.setMessage(self.errorIcons[0],self.errorSounds[0], "There are "+
                        str(nMeasure+nOther)+" basket weights for this species AND you have " +
                        "collected specimen data too. Are SURE you want permanatly delete this "
                        "species and ALL of these baskets and ALL of your specimen data?",'choice')
                if self.message.exec_():
                    #  user chose to delete the everything from this sample so first delete the specimen
                    ok = self.deleteSpecimen()

                    if not ok:
                        #  user changed their mind when we asked if they're sure - we're done here
                        return
            else:
                #  no specimen yet so we present a differently worded dialog. Only present a dialog
                #  if there are baskets though. Otherwise we just delete the sample.
                if nMeasure+nOther > 0:
                    self.message.setMessage(self.errorIcons[0],self.errorSounds[0], "There are "+
                            str(nMeasure+nOther)+" basket weights for this species. " +
                            "Are sure you want to permanantly delete ALL of them?", 'choice')
                    if not self.message.exec_():
                        #  user changed their mind
                        return

                    # kill the baskets
                    query =QtSql.QSqlQuery("DELETE FROM baskets WHERE ship="+self.ship+" AND survey="+
                            self.survey+" AND event_id="+self.activeHaul+" AND sample_id = "+
                            self.activeSampleKey, self.db)
                    self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+
                            query.lastQuery())

                #  try to delete from the catch summary and length histogram tables - these will be
                #  populated at this point if a user has come back into CLAMS to edit a past haul
                #  (depending on the execution path this might have already been done but it doesn't
                #  hurt to try again here.)
                query=QtSql.QSqlQuery("DELETE FROM catch_summary WHERE ship=" + self.ship +
                        " AND survey = " +self.survey + " AND event_id=" + self.activeHaul +
                        " AND sample_id ="+self.activeSampleKey)
                self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())
                query=QtSql.QSqlQuery("DELETE FROM length_histogram WHERE ship=" + self.ship +
                        " AND survey = " +self.survey + " AND event_id=" + self.activeHaul +
                        " AND sample_id ="+self.activeSampleKey)
                self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

                # delete the sample_data
                query =QtSql.QSqlQuery("DELETE FROM sample_data WHERE ship="+self.ship+" AND survey="+
                        self.survey+" AND event_id="+self.activeHaul+" AND sample_id = "+
                        self.activeSampleKey, self.db)
                self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+
                        query.lastQuery())

                #  and then delete the sample
                query =QtSql.QSqlQuery("DELETE FROM samples WHERE ship="+self.ship+" AND survey="+
                        self.survey+" AND event_id="+self.activeHaul+" AND sample_id = "+
                        self.activeSampleKey, self.db)
                self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+
                        ","+query.lastQuery())

            #  refresh the species list
            self.reloadSpeciesList()

        #  update the tables
        self.updateTables()


    def transferSample(self):
        self.freeze=True
        transDlg = transferdlg.TransferDlg(self)
        if not transDlg.exec_():# user cancelled action
            self.freeze=False
            return
        # write basket record
        if transDlg.fromType=='Count':
            count=str(-transDlg.transCount)
        else:
            count='NULL'
        query =QtSql.QSqlQuery("INSERT INTO baskets (ship, survey, event_id, sample_id, basket_type, count, weight, device_id) VALUES ("+
                    self.ship+", "+self.survey+","+self.activeHaul+","+transDlg.fromSampleKey+",'"+transDlg.fromType+"',"+count+","+str(-transDlg.transWeight)+","+
                    transDlg.transDevice+")",  self.db)

        self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())
        if transDlg.toType=='Count':
            count=str(transDlg.transCount)
        else:
            count='NULL'

        query =QtSql.QSqlQuery("INSERT INTO baskets (ship, survey, event_id, sample_id, basket_type, count, weight, device_id) VALUES ("+
                self.ship+", "+self.survey+","+self.activeHaul+","+transDlg.toSampleKey+",'"+transDlg.toType+"',"+count+","+str(transDlg.transWeight)+","+
                transDlg.transDevice+")",  self.db)
        self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())
        self.activeSampleKey=transDlg.toSampleKey
        # update basket table
        self.updateTables()
        self.freeze=False

    def editTable(self):
        pass
        self.freeze=True
        if self.activeSpcName=='mix1':# turn off count sample type for mixes
            self.validList[self.basketTypes.index('Count')]=0
        else:
            self.validList[self.basketTypes.index('Count')]=1

        self.typeDlg.buttonSetup(self.validList)

        columns=self.basketModel.columnCount(QModelIndex())
        row=self.basketView.currentIndex().row()
        if (row == -1):
            self.message.setMessage(self.errorIcons[2], self.errorSounds[1], "Please select a basket to edit " + self.firstName,'info')
            self.message.exec_()
            self.freeze = False
            return
        self.getBasketRow()
        header=['BASKET_ID','WEIGHT', 'COUNT', 'SAMPLE_TYPE' ]
        items=self.selRecord

        editDlg = basketeditdlg.BasketEditDlg(header,  items,  self)
        editDlg.exec_()
        if not editDlg.okFlag:# user cancelled action
            return
        # update database
        if editDlg.count=='-':
            editDlg.count='NULL'
        # update basket table
        query =QtSql.QSqlQuery("UPDATE baskets SET basket_type='"+editDlg.basketType+"', count = "+
                editDlg.count+", weight = "+editDlg.weight+"  WHERE ship="+self.ship+" AND survey="+self.survey+
                " AND event_id="+self.activeHaul+" AND sample_id = "+self.activeSampleKey+" AND basket_id = "+
                self.selRecord[0], self.db)
        self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

        self.freeze=False
        self.updateTables()


    def exitValidation(self):
        self.returnFlag=False
        for mixcode in ['100002', '100003', '100004']:
            query=QtSql.QSqlQuery("SELECT * FROM samples WHERE ship="+self.ship+" AND survey="+
                    self.survey+" AND event_id = "+self.activeHaul+" AND partition='"+
                    self.activePartition+"' AND species_code="+mixcode)
            if query.first():# there been a mix collected
                # mix validation
                (mixSubWeight, mixSpeciesWeight)=self.mixValidation(mixcode)
                if mixSubWeight==0:
                    self.message.setMessage(self.errorIcons[1],self.errorSounds[1], self.firstName+
                            ", there's no mix basket subsample weight for "+self.mixtureNames[mixcode]+" in the system.  Go do it now.", 'info')
                    self.message.exec_()
                    self.returnFlag=True
                    return

                #  check the mix parts more or less make up the weight of the total
                dev = (mixSubWeight - mixSpeciesWeight) / mixSubWeight * 100.
                #  check that the deviation is below the allowed value
                if (abs(dev) > float(self.settings[QString('MaxMixDev')])):
                    #  it is not, issue a warning and ask user what they want to do
                    self.message.setMessage(self.errorIcons[2], self.errorSounds[1], self.firstName+
                            ", the weight of the mix components is more or less than "+ str(dev) +
                            " % of the mix subsample weight for  "+self.mixtureNames[mixcode]+". Does this bother you? ", 'choice')
                    if self.message.exec_():
                        #  user is bothered by this - set the failed validation flag
                        self.returnFlag=True
                    else:
                        if mixcode in self.parentSamples:
                            #  user doesn't care, make note of this and move on
                            QtSql.QSqlQuery("INSERT INTO override (scientist, record_id, " +
                                    "table_name,description) VALUES ('" + self.scientist + "'," +
                                    self.parentSamples[mixcode] + ",'sample', 'mix components are "+str(dev)+
                                    " % less than the mix subsample weight')")

        # closing  validation - get species in list

        query=QtSql.QSqlQuery("SELECT species.common_name, samples.sample_id, samples.species_code, " +
                "samples.subcategory  FROM samples, species WHERE species.species_code=samples.species_code " +
                " AND samples.sample_type in ('Mix1','SubMix1','Mix2','Species') AND samples.ship=" + self.ship + " AND samples.survey=" + self.survey + " AND samples.event_id = " +
                self.activeHaul + " AND samples.partition='" + self.activePartition + "'")
        while query.next():
            query1 = QtSql.QSqlQuery("SELECT * FROM baskets WHERE ship="+self.ship+" AND survey="+
                    self.survey+" AND event_id = "+self.activeHaul+" AND sample_id = "+
                    query.value(1).toString())

            if not query1.next(): # no baskets for this species
                if query.value(3).toString()<>'None':
                    spcName=query.value(0).toString()+" "+query.value(3).toString()
                else:
                    spcName=query.value(0).toString()
                self.message.setMessage(self.errorIcons[1],self.errorSounds[1], "My dear "+self.firstName+
                        ", There are are no basket weights for "+spcName+". Does this bother you?", 'choice')
                if self.message.exec_():
                        self.returnFlag=True
                        return
                # we're commenting this out because its caousing problems with multi catch input
#                    else:
#                        # remove stray sample record
#                        query =QtSql.QSqlQuery("DELETE FROM samples WHERE ship="+self.ship+" AND survey="+
#                                        self.survey+" AND event_id = "+self.activeHaul+" AND sample_id = "+query.value(1).toString(),  self.db)
#                        self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())


    def mixValidation(self,  mixcode):
        # validation #2 mix sub weight vs species in it
        mixSubWeight=0
        #get mix sample key
        query = QtSql.QSqlQuery("SELECT sample_id FROM samples WHERE samples.species_code="+mixcode+" AND ship="+self.ship+" AND survey="+
                                        self.survey+" AND event_id = "+self.activeHaul+" AND partition='"+self.activePartition+"'")
        if query.first():# there is a mix on this tow
            mixKey=query.value(0).toString()
            query1 = QtSql.QSqlQuery("SELECT Sum(weight) FROM baskets WHERE ship="+self.ship+" AND survey="+
                                        self.survey+" AND event_id = "+self.activeHaul+" AND sample_id="+mixKey+
            " AND basket_type = 'Measure'")
            # check for a mix subsample weight
            query1.first()
            mixSubWeight=(float(query1.value(0).toString()))
        else: #there's no mix
            return

        mixSpeciesWeight=0
        query = QtSql.QSqlQuery("SELECT Sum(baskets.weight) FROM samples, baskets WHERE samples.sample_id = "+
        "baskets.sample_id AND samples.ship=baskets.ship AND samples.survey=baskets.survey AND samples.event_id=baskets.event_id AND samples.ship="+self.ship+" AND samples.survey="+
        self.survey+" AND samples.event_id="+self.activeHaul+" AND samples.partition='"+self.activePartition+"' AND samples.parent_sample="+mixKey)# check for a mix subsample weight
        if query.first():
            mixSpeciesWeight=(float(query.value(0).toString()))

        return mixSubWeight, mixSpeciesWeight



    def reloadSpeciesList(self):

        #  disconnect the selection changed signal so we don't trigger it when the list is
        #  cleared.
        self.disconnect(self.speciesList, SIGNAL("itemSelectionChanged()"), self.getActiveSpc)

        # add just species
        self.speciesList.clearContents()
        self.speciesList.setRowCount(0)
        self.speciesDict={}

        # get species involved
        query=QtSql.QSqlQuery("SELECT samples.sample_id, species.common_name, species.scientific_name," +
                "species.species_code, samples.parent_sample, samples.subcategory"+
                " FROM samples, species WHERE samples.species_code=species.species_code AND " +
                "samples.ship="+self.ship+" AND samples.survey="+
        self.survey+" AND samples.event_id="+self.activeHaul+" AND samples.partition='"+
                self.activePartition+"' AND samples.species_code not in (100000,100001) ORDER BY samples.sample_id ASC")
        cnt=0
        while query.next():
            #get the namespace
            query0=QtSql.QSqlQuery("SELECT PARAMETER_VALUE FROM sample_data WHERE sample_parameter=" +
                    "'sample_name' AND  sample_id="+ query.value(0).toString())
            if query0.first():
                if query0.value(0).toString()=='scientific':
                    species=query.value(2).toString()
                else:
                    species=query.value(1).toString()
            else:
                species=query.value(1).toString()
            subcat=query.value(5).toString()
            if subcat<>'None':
                name=species+'-'+subcat
            else:
                name=species
            # what's the parent sample Name

            query1=QtSql.QSqlQuery("SELECT b.common_name FROM samples a JOIN species b ON a.species_code=b.species_code WHERE a.ship="+self.ship+" AND a.survey="+
                    self.survey+" AND a.event_id = "+self.activeHaul+" AND a.sample_id="+query.value(4).toString() + "")
            if query1.first():
                myParent=query1.value(0).toString()
            else:
                myParent=''
            self.speciesList.insertRow(cnt)
            self.speciesList.setVerticalHeaderItem(cnt,QTableWidgetItem(query.value(0).toString()))
            self.speciesList.setItem(cnt, 0, QTableWidgetItem(name))
            self.speciesList.setItem(cnt, 1, QTableWidgetItem(myParent))
            cnt=cnt+1
            self.speciesDict.update({str(species):str(query.value(3).toString())})
        self.speciesList.resizeColumnsToContents()
        self.picLabel.clear()

        #  reconnect the selection changed signal now that we're done changing the list
        self.connect(self.speciesList, SIGNAL("itemSelectionChanged()"), self.getActiveSpc)
        self.speciesList.scrollToBottom()


    def loadDeviceSounds(self):
        '''loadDeviceSounds queries the db for the device sound files used for
        this module. It also populates a list of devices configured for this station.
        '''

        self.devices = []
        self.sounds = {}

        #  query the device ID and sound file for each device
        sql = ("SELECT measurement_setup.device_id, device_configuration.parameter_value FROM " +
                "device_configuration INNER JOIN measurement_setup ON device_configuration.device_id " +
                "= measurement_setup.device_id WHERE measurement_setup.workstation_id=" +
                self.workStation+" AND measurement_setup.gui_module='Catch' AND " +
                "device_configuration.device_parameter = 'SoundFile'")
        query = self.db.dbQuery(sql)
        for device_id, parameter_value in query.next():
            self.devices.append(device_id)
            hasExt = parameter_value.split('.')
            if len(hasExt) > 1:
                soundFile = self.settings['SoundsDir'] + parameter_value
            else:
                soundFile = self.settings['SoundsDir'] + parameter_value + '.wav'
            soundEffect = QSoundEffect()
            soundEffect.setSource(QUrl.fromLocalFile(soundFile))
            self.sounds[device_id] = soundEffect


    def printLabel(self):
        '''
            printLabel prints a label for whole fish samples
        '''

        #  ensure that a species is selcted
        if (self.activeSpcName == None):
            #  no species selected - show error dialog
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2], "Hey " + self.firstName +
                                    " pick a species. Duh, even I know that.", 'info')
            self.message.exec_()
            return
        else:

            # get species code from db
            speciesCode = self.activeSpcCode=self.speciesDict[str(self.activeSpcName)]

            #get eq_time
            query=QtSql.QSqlQuery("SELECT event_data.PARAMETER_VALUE FROM event_data  WHERE " +
                "(event_data.SHIP="+self.ship+") AND (event_data.SURVEY="+self.survey+
                ") AND (event_data.event_id="+self.activeHaul+") AND "+
                "(event_data.PARTITION='"+self.activePartition+"') AND "+
                "(event_data.event_parameter='EQ')")
            if query.first():
                EQDateTime = query.value(0).toString()
                EQDate = EQDateTime.split(' ')[0]
            else:
                EQDate = ''


            #  ask how many fish are being frozen
            self.numpad.msgLabel.setText("How many " + self.activeSpcName + " are you freezing?")
            if not self.numpad.exec_():
                return
            number = self.numpad.value

            data={'title':'NOAA/AFSC/RACE/MACE',
                  'ship':self.ship,
                  'survey':self.survey,
                  'haul':self.activeHaul,
                  'species_code':speciesCode,
                  'common_name':self.activeSpcName,
                  'date':EQDate,
                  'sample_type':'whole fish',
                  'count':number,
                  'scientist':self.scientist
                 }

            #  print the label
            self.printer.printSpecialSampleLabel2(data)

            # print sound
            if self.printSound:
                self.printSound.play()


    def getComment(self):
        keyDialog = keypad.KeyPad(self.comment,  self)
        keyDialog.exec_()
        if keyDialog.okFlag:
            string=keyDialog.dispEdit.toPlainText()
            self.comment=keyDialog.dispEdit.toPlainText()
            string=string.split('\n')
            p=''
            for s in string:
                p=p+s+' '

            # insert comment into sample
            QtSql.QSqlQuery("UPDATE samples SET comments='" + p + "' WHERE ship="+self.ship +
                    " AND survey=" + self.survey + " AND event_id = " + self.activeHaul +
                    " AND sample_id = "+self.activeSampleKey)


    def goExit(self):
        self.close()

    def closeEvent(self, event):
        self.exitValidation()
        #self.refreshTimer.stop()
        if self.returnFlag:
            event.ignore()
        else:
            event.accept()


    def checkWindowLocation(self, position, size, padding=[5, 25]):
        '''
        checkWindowLocation accepts a window position (QPoint) and size (QSize)
        and returns a potentially new position and size if the window is currently
        positioned off the screen.

        This function uses QScreen.availableVirtualGeometry() which returns the full
        available desktop space *not* including taskbar. For all single and "typical"
        multi-monitor setups this should work reasonably well. But for multi-monitor
        setups where the monitors may be different resolutions, have different
        orientations or different scaling factors, the app may still fall partially
        or totally offscreen. A more thorough check gets complicated, so hopefully
        those cases are very rare.

        If the user is holding the <shift> key while this method is run, the
        application will be forced to the primary monitor.
        '''

        #  create a QRect that represents the app window
        appRect = QRect(position, size)

        #  check for the shift key which we use to force a move to the primary screem
        resetPosition = QGuiApplication.queryKeyboardModifiers() == Qt.KeyboardModifier.ShiftModifier
        if resetPosition:
            position = QPoint(padding[0], padding[0])

        #  get a reference to the primary system screen - If the app is off the screen, we
        #  will restore it to the primary screen
        primaryScreen = QGuiApplication.primaryScreen()

        #  assume the new and old positions are the same
        newPosition = position
        newSize = size

        #  Get the desktop geometry. We'll use availableVirtualGeometry to get the full
        #  desktop rect but note that if the monitors are different resolutions or have
        #  different scaling, some parts of this rect can still be offscreen.
        screenGeometry = primaryScreen.availableVirtualGeometry()

        #  if the app is partially or totally off screen or we're force resetting
        if resetPosition or not screenGeometry.contains(appRect):

            #  check if the upper left corner of the window is off the left side of the screen
            if position.x() < screenGeometry.x():
                newPosition.setX(screenGeometry.x() + padding[0])
            #  check if the upper right is off the right side of the screen
            if position.x() + size.width() >= screenGeometry.width():
                p = screenGeometry.width() - size.width() - padding[0]
                if p < padding[0]:
                    p = padding[0]
                newPosition.setX(p)
            #  check if the top of the window is off the top/bottom of the screen
            if position.y() < screenGeometry.y():
                newPosition.setY(screenGeometry.y() + padding[0])
            if position.y() + size.height() >= screenGeometry.height():
                p = screenGeometry.height() - size.height() - padding[1]
                if p < padding[0]:
                    p = padding[0]
                newPosition.setY(p)

            #  now make sure the lower right (resize handle) is on the screen
            if (newPosition.x() + newSize.width()) > screenGeometry.width():
                newSize.setWidth(screenGeometry.width() - newPosition.x() - padding[0])
            if (newPosition.y() + newSize.height()) > screenGeometry.height():
                newSize.setHeight(screenGeometry.height() - newPosition.y() - padding[1])

        return [newPosition, newSize]



