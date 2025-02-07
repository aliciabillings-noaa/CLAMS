#!/usr/bin/env python
"""
CLAMSsbeDownloader is a replacement for the MACE SBE download program. This is a
further extension of the MACE mini Downloader used in 2015 which has been modified
to work exclusively with CLAMS. It does not offer the option to download to a text
file and requires a connection to CLAMS and active survey, ship, and haul values
must exists in the application_configuration table.

Also note that this application will attempt to get the latitude to use for pressure
to depth conversions from the EQLatitude parameter in the event_data table. If this
parameter doesn't exist for the active event, it will use a default value of 56.
"""

#  import dependent modules
import os
import sys
import math
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ui import ui_CLAMSsbeDownloader
import sbeSetInterval
import sbeSetLocation
from acquisition.serial import sbe39
from acquisition.serial import sbeProgressDialog
from acquisition.serial import selectWinPortDialog
import dbConnection


class CLAMSsbeDownloader(QMainWindow, ui_CLAMSsbeDownloader.Ui_sbeDownloader):

    def __init__(self, dataSource, schema, user, password, parent=None):
        super(CLAMSsbeDownloader, self).__init__(parent)
        self.setupUi(self)

        #  Initialize variables and define constants
        self.dataTextBuffer = []
        self.connecting = False
        self.serialNumber = ''
        self.__maxDataTextLines = 500
        self.downloadErrors = 0
        self.maxDownloadErrors = 25

        #  connection parameters
        self.dbName  = dataSource
        self.schema = schema
        self.userID  = user
        self.pswd  =  password

        #  create an instance of our dbConnection class
        self.db = dbConnection.dbConnection(self.dbName, self.userID, self.pswd)

        #  restore the application state
        self.appSettings = QSettings('afsc.noaa.gov', 'CLAMSsbeDownloader')
        size = self.appSettings.value('winsize', QSize(690,700)).toSize()
        self.resize(size)
        position = self.appSettings.value('winposition', QPoint(5,5)).toPoint()
        self.move(position)
        self.__dataDir = self.appSettings.value('datadir', QDir.home().path()).toString()
        self.comPort  = str(self.appSettings.value('comport', 'COM4').toString())
        baud  = self.appSettings.value('baud', 9600).toInt()
        if (baud[1]):
            self.baud  = baud[0]
        else:
            self.baud  = 9600

        #  add the COM port settings display in the status bar
        self.COMSettingsLabel = QLabel('')
        self.statusbar.addPermanentWidget(self.COMSettingsLabel)
        self.COMSettingsLabel.setText('COM Settings: ' + self.comPort + ', ' + str(self.baud))

        #  create an instance of the set interval dialog
        self.sbeIntervalDlg = sbeSetInterval.sbeSetInterval()

        #  connect the dialog's sbeSetInterval signal - emitted when the user clicks o.k.
        #  on the sbeSetInterval dialog
        self.connect(self.sbeIntervalDlg, SIGNAL("sbeSetInterval"), self.intervalSet)

        #  create an instance of the SBE39 class and connect siganls
        self.sbe = sbe39.sbe39(self.comPort, baud=self.baud)

        #  connect the SBE39 signals
        self.connect(self.sbe, SIGNAL("SBEConnected"), self.connected)
        self.connect(self.sbe, SIGNAL("SBETimeout"), self.sbeTimeout)
        self.connect(self.sbe, SIGNAL("SBEData"), self.showSBEData)
        self.connect(self.sbe, SIGNAL("SBEStatus"), self.sbeStatusUpdate)
        self.connect(self.sbe, SIGNAL("SBEProgress"), self.showProgress)
        self.connect(self.sbe, SIGNAL("SBEDownloadComplete"), self.downloadComplete)
        self.connect(self.sbe, SIGNAL("SBEDownloadData"), self.downloadingData)
        self.connect(self.sbe, SIGNAL("SBEAbort"), self.downloadAbort)

        #  connect this GUI's button signals
        self.connect(self.actionExit, SIGNAL("triggered()"), SLOT('close()'))
        self.connect(self.actionSetInterval, SIGNAL("triggered()"), self.setInterval)
        self.connect(self.actionSetComPort, SIGNAL("triggered()"), self.configureComPort)
        self.connect(self.statusButton, SIGNAL("clicked()"), self.getStatus)
        self.connect(self.downloadButton, SIGNAL("clicked()"), self.startDownload)
        self.connect(self.doneBtn, SIGNAL("clicked()"), self.close)
        self.connect(self.connectButton, SIGNAL("clicked()"), self.connectToSBE)
        self.connect(self.startButton, SIGNAL("clicked()"), self.startLogging)
        self.connect(self.stopButton, SIGNAL("clicked()"), self.stopLogging)

        #  set up the button states
        self.setGUIButtons(False)

        #  set the base directory path - this is the full path to this application
        self.baseDir = reduce(lambda l,r: l + os.path.sep + r,
                              os.path.dirname(os.path.realpath(__file__)).split(os.path.sep))
        #  set the window icon
        try:
            self.setWindowIcon(QIcon(self.baseDir + os.sep + 'icons/giant_clam.png'))
        except:
            pass

        #  create an instance of the SBE progress dialog - this dialog shows download progress
        #  and it also has an abort button. You pass it the reference to the sbe object and it
        #  handles the signals internally. You just need to show and hide it.
        self.sbeProgress = sbeProgressDialog.sbeProgressDialog(self.sbe, parent=self)

        #  start a timer event to connect to the database
        startTimer = QTimer(self)
        startTimer.setSingleShot(True)
        self.connect(startTimer, SIGNAL("timeout()"), self.startApplication)
        startTimer.start(0)


    def startApplication(self):

        try:
            self.db.dbOpen()
        except Exception as err:
            QMessageBox.critical(self,"ERROR", "Unable to connect to the database. " + err.error)
            self.close()
            return

        #  determine our hostname and query database for workstation number
        computerName = os.getenv("COMPUTERNAME")
        query = self.db.dbQuery("SELECT workstation_id FROM " + self.schema + ".workstations WHERE hostname ='" +
                                computerName + "'")
        query_val= query.first()
        if not query_val:
            iconPath, hasIconPath = checkPath(None, 'icons')
            soundsPath, hasSoundsPath = checkPath(None, 'sounds')
        else:
            #  read in workstation specific settings
            self.workStation, = query_val

            #  get the icon dir
            query = self.db.dbQuery("SELECT parameter_value FROM " + self.schema + ".workstation_configuration " +
                                "WHERE workstation_ID = " + self.workStation + " AND parameter='IconDir'")
            query_val = query.first()
            if not query_val:
                iconPath, hasIconPath = self.checkPath(None, 'icons')
            else:
                path, = query_val
                iconPath, hasIconPath = self.checkPath(path, 'icons')

            #  get the sounds dir
            query = self.db.dbQuery("SELECT parameter_value FROM " + self.schema + ".workstation_configuration " +
                                "WHERE workstation_ID = " + self.workStation + " AND parameter='SoundsDir'")
            query_val = query.first()
            if not query_val:
                soundsPath, hasSoundsPath = self.checkPath(None, 'sounds')
            else:
                path, = query_val
                soundsPath, hasSoundsPath = self.checkPath(path, 'sounds')

        #  load icons and sounds
        if (hasIconPath):
            icon = QImage(iconPath + "plankton.png")
            icon = icon.scaledToHeight(self.imgLabel.height(), Qt.SmoothTransformation)
            self.imgLabel.setPixmap(QPixmap.fromImage(icon.mirrored(horizontal=True,
                    vertical=False)))
        if (hasSoundsPath):
            self.completeSound = QSound(soundsPath + 'dp_starwars_yahoo.wav')

        # populate from active ship, survey, and event stuff
        query = self.db.dbQuery("SELECT parameter_value FROM application_configuration WHERE parameter='ActiveShip'")
        ship, = query.first()
        self.shipLabel.setText(ship)
        query = self.db.dbQuery("SELECT parameter_value FROM application_configuration WHERE parameter='ActiveSurvey'")
        survey, = query.first()
        self.surveyLabel.setText(survey)
        query = self.db.dbQuery("SELECT parameter_value FROM application_configuration WHERE parameter='ActiveEvent'")
        query_val = query.first()
        if (not query_val):
            QMessageBox.critical(self,"ERROR", "No active event. I cannot download data without an active event.")
            self.close()
            return
        else:
            event, = query_val
            self.haulLabel.setText(event)

        #  get the latitude of this event
        query = self.db.dbQuery("SELECT parameter_value FROM event_data WHERE ship = " + ship + " and survey =" + survey +
                " and event_id =" + event + " and event_parameter = 'EQLatitude'")
        query_val = query.first()
        if (not query_val):
            #  event doesn't have an EQ entry, use default value
            self.haulLat = 56.0
        else:
            try:
                self.haulLat = float(query_val[0])
            except:
                #  value couldn't be converted to a float - use default value
                self.haulLat = 56.0


    def configureComPort(self):

        dialog = selectWinPortDialog.selectWinPortDialog(defaultPort=self.comPort,
                    defaultBaud=self.baud)
        ok = dialog.exec_()
        if (ok):
            #  update the serial params
            self.comPort = dialog.port
            self.baud = dialog.baud
            self.sbe.setConnectionParams(self.comPort, self.baud)

            #  update the application settings
            self.appSettings.setValue('comport', self.comPort)
            self.appSettings.setValue('baud', self.baud)

            #  update the GUI
            self.COMSettingsLabel.setText('COM Settings: ' + self.comPort + ', ' + str(self.baud))


    def showProgress(self, device, pctComplete):
        #  this is just here as a stub since we're using the SBE progress dialog to display
        #  progress. If you use the SBE progress dialog you don't need to connect the progress
        #  signal nor implement this function
        pass


    def downloadComplete(self, device, nDownloaded, nDropped):

        #  hide and reset the progress dialog
        self.sbeProgress.hide()
        self.sbeProgress.reset()

        #  reconnect the SBEData signal
        self.connect(self.sbe, SIGNAL("SBEData"), self.showSBEData)

        #  report our results
        if nDownloaded > 2:
            # Compute averages to be inserted into the event_data table
            self.computeAverages()

            #  play the download complete sound
            self.completeSound.play()

            #  report success
            QMessageBox.information(self, 'Success', str(nDownloaded) + ' measurements ' +
                    'downloaded successfully.')
        else:
            QMessageBox.critical(self, 'ERROR', str(nDownloaded)+' measurements downloaded. ' +
                    'Try stopping the SBE from recording and THEN press download.')


    def downloadAbort(self):

        #  hide and reset the progress dialog
        self.sbeProgress.hide()
        self.sbeProgress.reset()

        #  reconnect the SBEData signal
        self.connect(self.sbe, SIGNAL("SBEData"), self.showSBEData)

        #  show a temporary message on the status bar
        self.statusbar.showMessage('Downloading aborted.', 5000)


    def downloadingData(self, device, line):

        try:
            #  build the time string
            mdy = '{:02d}/{:02d}/{:04d}'.format(line[0].month, line[0].day, line[0].year)
            hms = '{:02d}:{:02d}:{:02d}'.format(line[0].hour, line[0].minute, line[0].second +
                                                    int(round(line[0].microsecond/1000000.)))
            time = mdy + " " + hms

            #  calculate depth from pressure
            depth = round(self.pressureToDepth(line[2], self.haulLat), 3)

            #  insert data into database
            sql = ("INSERT INTO clamsbase2.event_stream_data (ship, survey, event_id, device_id, " +
                    "time_stamp, measurement_type, measurement_value) VALUES (" + self.shipLabel.text() +
                    "," + self.surveyLabel.text() + "," + self.haulLabel.text() + "," + self.device_id +
                    ",TO_TIMESTAMP('" + time + "','MM/DD/YYYY HH24:MI:SS.FF'),'SBETemperature','" +
                    str(line[1]) + "')")
            self.db.dbExec(sql)
            sql =("INSERT INTO clamsbase2.event_stream_data (ship, survey, event_id, device_id, " +
                    "time_stamp, measurement_type, measurement_value) VALUES ("+self.shipLabel.text() +
                    "," + self.surveyLabel.text() + "," + self.haulLabel.text() + "," + self.device_id +
                    ",TO_TIMESTAMP('"+time+"','MM/DD/YYYY HH24:MI:SS.FF'),'SBEDepth','"+str(depth)+"')")
            self.db.dbExec(sql)

    #  As of Winter 2016 we are no longer inserting pressure into the event_stream_data table
    #  to minimize the volume of data going into the table.
    #            sql =("INSERT INTO clamsbase2.event_stream_data (ship, survey, event_id, device_id, " +
    #                    "time_stamp, measurement_type, measurement_value) VALUES (" + self.shipLabel.text() +
    #                    "," + self.surveyLabel.text() + "," + self.haulLabel.text() + "," + self.device_id +
    #                    ",TO_TIMESTAMP('" + time + "','MM/DD/YYYY HH24:MI:SS.FF'),'SBEPressure','" +
    #                    str(line[2]) + "')")
    #            self.db.dbExec(sql)

        except Exception, e:
            #  there was an error
           self.sbe.abort()
           self.downloadAbort()
           QMessageBox.critical(self, 'Download Aborted', 'Unable to insert data into database.' + str(e))


    def connectToSBE(self):

        if (self.sbe.connected == False):
            #  we're connecting to the SBE - attempt to connect to the SBE
            try:
                self.serialNumber = ''
                self.statusbar.showMessage('Trying to wake SBE...')
                self.connecting = True
                self.sbe.connect()
            except Exception:
                 QMessageBox.critical(self, 'Error', 'Unable to open COM port ' + str(self.comPort))
                 self.statusbar.showMessage('')
        else:
            #  we need to disconnect from the SBE
            self.sbe.disconnect()

            #  update the GUI
            self.setGUIButtons(False)


    def connected(self, device):

        #  show a temporary message on the status bar
        self.statusbar.showMessage('Connected to ' + device, 10000)

        #  get the SBE status
        self.sbe.getStatus()

        #  set up the GUI
        self.setGUIButtons(True)


    def pressureToDepth(self, p, lat):
        '''
        calculates depth based on latitude and pressure. From:
        Unesco 1983. Algorithms for computation of fundamental properties of
        seawater, 1983. _Unesco Tech. Pap. in Mar. Sci._, No. 44, 53 pp.
        '''

        deg2rad = math.pi / 180.0

        # Eqn 25, p26.  UNESCO 1983.
        c = [9.72659, -2.2512e-5, 2.279e-10, -1.82e-15]
        gam_dash = 2.184e-6

        lat = abs(lat)
        X = math.sin(lat * deg2rad)
        X = X * X

        bot_line = (9.780318 * (1.0 + (5.2788e-3 + 2.36e-5 * X) * X) +
                    gam_dash * 0.5 * p)
        top_line = (((c[3] * p + c[2]) * p + c[1]) * p + c[0]) * p

        return top_line / bot_line


    def sbeStatusUpdate(self, deviceName, status):
        '''
        sbeStatusUpdate is called when we receive the results of a status request.
        We only care about the details when we are connecting to the SBE since
        that is when we extract the serial number. Otherwise we don't do anything.
        '''

        if (self.connecting):
            #  if we're in the process of connecting, get this SBE's device ID from CLAMS
            self.connecting = False

            self.serialNumber = status['serial number']

            # get clamsbase device id for this sbe
            query = self.db.dbQuery("SELECT device_id FROM devices WHERE model like 'SBE39%' AND serial_number='" +
                    self.serialNumber + "'")
            self.device_id, = query.first()

            #  if we can't find one, disconnect and issue error
            if (self.device_id == None):
                #  disconnect
                self.sbe.disconnect()

                #  update the GUI
                self.setGUIButtons(False)

                #  issue the error
                QMessageBox.critical(self, 'Error', "Can't find an SBE with serial number " + self.serialNumber +
                        " in the DEVICES table.\nPlease add this device before downloading.")


    def startLogging(self):
        ok = QMessageBox.question(self, 'Start Logging', 'Reset the sample number to 0 and start logging? \n' +
                                      'Existing data will be overwritten!', QMessageBox.Ok | QMessageBox.Cancel)
        if (ok == QMessageBox.Ok):
            # set the sample number to 0
            self.sbe.setSampleNumber(0)

            #  set the SBE clock
            self.sbe.setRTC()

            #  start logging
            self.sbe.startNow()

        #  DO NOT INTERACT WITH THE SBE AFTER STARTING TO LOG BECAUSE
        #  IT WILL CAUSE THE SBE TO TEMPORARILY STOP LOGGING WHILE IT
        #  SITS IN 'COMMAND' MODE. (It will eventually start logging
        #  again after it times out of command mode after 2 or 3
        #  minutes but it's best just to avoid sending any commands
        #  at this point.)


    def stopLogging(self):

        #  stop the SBE logging
        self.sbe.stop()

        #  update the status in the GUI
        self.sbe.getStatus()


    def sbeTimeout(self):

        #  issue an error
        QMessageBox.critical(self, 'Error', 'Unable to connect or lost connection to SBE on ' + str(self.comPort))

        #  disconnect the SBE
        self.sbe.disconnect()

        #  update the GUI
        self.setGUIButtons(False)


    def intervalSet(self, interval, rto):
        #  this method is called when the sbeSetInterval signal is received meaning the
        #  user has set a new sampling interval.

        self.sbe.setSamplingInterval(interval)
        self.sbe.setTxRealTime(rto)

        #  update the status in the GUI
        self.sbe.getStatus()


    def setInterval(self):

        #  get the current interval and RealTime Output values
        rtoText = self.sbe.status.get('real-time output', 'not')
        if (rtoText.lower().find('not') > -1) or (rtoText.lower().find('disabled') > -1):
            rto = False
        else:
            rto = True
        interval = int(self.sbe.status.get('sample interval', '0').split()[0])

        #  set the values in the dialog and show
        self.sbeIntervalDlg.setInterval(interval, rto)
        self.sbeIntervalDlg.show()


    def setGUIButtons(self, state):
        '''
        setGUIButtons sets the state of the GUI elements based on the connection
        state. True if we're connected to the SBE and False if not.
        '''

        if (state):
            self.connectButton.setText('Disconnect')

        else:
            self.connectButton.setText('Connect')

        self.actionSetComPort.setEnabled(not state)
        self.actionSetInterval.setEnabled(state)
        self.statusButton.setEnabled(state)
        self.startButton.setEnabled(state)
        self.stopButton.setEnabled(state)
        self.downloadButton.setEnabled(state)


    def getStatus(self):
        '''
        getStatus requests the status from the SBE.
        '''
        self.sbe.getStatus()


    def startDownload(self):
        '''
        startDownload attempts to start the SBE download process. It first checks for
        existing data, asking the user if they want to overwrite if found, and then it
        disconnects the SBEData signal (so we don't flood the console with data strings)
        and then tells the SBE class to download.
        '''

        #  7-26-18 - RHT: Added a dialog which gets the SBE mounting location and
        #  create an instance of the set location dialog
        sbeLocationlDlg = sbeSetLocation.sbeSetLocation()
        sbeLocationlDlg.exec()

        #  make sure that the user specified a location
        if (sbeLocationlDlg.location is None):
            #  no location specified
            return

        #  set the location
        self.sbeLocation = sbeLocationlDlg.location

        try:

#  8-6-18: RHT - Added SBE location to haul_data. Location is the first thing to be
#                inserted when downloading and it is possible that location gets inserted
#                but no data downloaded so we have to look for location to determine if
#                data has already been downloaded.
#
#            # check for existing data for this haul
#            query = self.db.dbQuery("SELECT measurement_value FROM event_stream_data WHERE ship=" +
#                    self.shipLabel.text() + " AND survey="+self.surveyLabel.text() + " AND event_id=" +
#                    self.haulLabel.text() + " AND device_id=" + self.device_id + " AND " +
#                    "(measurement_type='SBEPressure' OR measurement_type='SBETemperature' OR measurement_type='SBEDepth')")
#            data, = query.first()
#
            #  determine if this data has already been downloaded
            sql = ("SELECT event_parameter FROM event_data WHERE ship=" + self.shipLabel.text() +
                    " AND survey=" + self.surveyLabel.text() + " AND event_id=" + self.haulLabel.text() +
                    " AND event_parameter like '%SBE' AND parameter_value='" + self.serialNumber + "'")
            mountingLocQuery = self.db.dbQuery(sql)
            mountingLoc, = mountingLocQuery.first()

            if (mountingLoc != None):
                reply = QMessageBox.question(self, 'Warning!',"<font size = 14> You already downloaded SBE " +
                        "data for this haul and SBE device.  Do you want to overwrite? </font>",
                        QMessageBox.Yes, QMessageBox.No)
                if (reply == QMessageBox.Yes):

                    #  get the parameters names for the previous mounting location
                    avgDepthParam, avgTempParam = self.getAveragesParamNames(mountingLoc)

                    #  now we can clear out old data
                    sql = ("DELETE FROM event_stream_data WHERE ship=" + self.shipLabel.text() + " AND survey=" +
                            self.surveyLabel.text() + " AND event_id=" + self.haulLabel.text() + " AND device_id=" +
                            self.device_id)
                    self.db.dbExec(sql)
                    #  and clear out the old average data as well
                    sql = ("DELETE FROM event_data WHERE ship=" + self.shipLabel.text() + " AND survey=" +
                            self.surveyLabel.text() + " AND event_id=" + self.haulLabel.text() + " AND " +
                            "event_parameter='" + avgDepthParam + "'")
                    self.db.dbExec(sql)
                    sql = ("DELETE FROM event_data WHERE ship=" + self.shipLabel.text() + " AND survey=" +
                            self.surveyLabel.text() + " AND event_id=" + self.haulLabel.text() + " AND " +
                            "event_parameter='" + avgTempParam + "'")
                    self.db.dbExec(sql)

                    #  and lastly, clear out the mounting location
                    sql = ("DELETE FROM event_data WHERE ship=" + self.shipLabel.text() + " AND survey=" +
                            self.surveyLabel.text() + " AND event_id=" + self.haulLabel.text() + " AND " +
                            "event_parameter like '%SBE' AND parameter_value='" + self.serialNumber + "'")
                    self.db.dbExec(sql)

                else:
                    #  user chose not to overwrite
                    return

            #  insert the SBE mounting location into haul_data
            self.db.dbQuery("INSERT INTO event_data (ship,  survey, event_id, partition, " +
                "event_parameter,  parameter_value) VALUES("+ self.shipLabel.text() +
                "," + self.surveyLabel.text() + ","+self.haulLabel.text() + ",'Codend','" +
                self.sbeLocation + "','"+ self.serialNumber +"')")

            #  show the progess dialog
            self.sbeProgress.show()

            #  disconnect the SBEData signal since displaying the data during
            #  download slows the download down significantly.
            self.disconnect(self.sbe, SIGNAL("SBEData"), self.showSBEData)

            #  download all samples for previous logging session - calling download with
            #  no arguments will download all samples from 0 to the current sample.
            #  NOTE THAT YOU MUST UPDATE THE STATUS OF THE DEVICE AFTER IT IS STOPPED TO
            #  MAKE SURE THAT SAMPLE NUMBER IS UP TO DATE.
            self.downloadErrors = 0
            self.sbe.download()

        except Exception as err:
            #  there was an error
            QMessageBox.critical(self, 'Error', 'Error downloading data: ' + str(err))


    def showSBEData(self, name, val, color='black'):

        if val:
            if False:
                #  Display output in HTML. This results in the removal of all tags from the
                #  xml based real time display. That's not that big of a deal
                text = '<text style="color:' + color + '>' + val + '<br />'
                self.dataTextBuffer.append(text)
                if len(self.dataTextBuffer) > self.__maxDataTextLines:
                    self.dataTextBuffer.pop(0)
                text = ''.join(self.dataTextBuffer)
                text = QString('<html><body><p>' + text + '</p></body></html>')
                self.dataText.setHtml(text)
            else:
                #  Display the output in plain text
                self.dataTextBuffer.append(val)
                if len(self.dataTextBuffer) > self.__maxDataTextLines:
                    self.dataTextBuffer.pop(0)
                text = '\n'.join(self.dataTextBuffer)
                self.dataText.setPlainText(text)

            #  ensure that the window is scrolled to see the new line of text.
            self.dataText.verticalScrollBar().setValue(self.dataText.verticalScrollBar().maximum())


    def closeEvent(self, event=None):

        self.sbe.disconnect()
        if self.db:
            self.db.dbClose()
        self.appSettings.setValue('winposition', self.pos())
        self.appSettings.setValue('winsize', self.size())
        self.appSettings.setValue('datadir', self.__dataDir)
        self.appSettings.setValue('comport',self.comPort)
        self.appSettings.setValue('baud',self.baud)


    def getAveragesParamNames(self, locationName):
        '''
        getAveragesParamNames returns the event_parameters used to store the
        averages computed for the specified SBE mounting location. Since
        there isn't a straightforward way to identify these params in the
        event_parameters table and link them to their mounting location, and
        the fact that we'll only have a handful, we're hard coding them here.

        This method is used both when deleting existing data and inserting
        averages for just downloaded data.
        '''

        #  set the event_parameters based on the mountng location
        if (locationName == 'HeadropeSBE'):
            avgDepthParam = 'AvgSBEHeadRopeDepth'
            avgTempParam = 'AvgSBEHeadRopeTemp'
        elif (locationName == 'FootropeSBE'):
            avgDepthParam = 'AvgSBEFootRopeDepth'
            avgTempParam = 'AvgSBEFootRopeTemp'
        elif (locationName == 'DropTSSBE'):
            avgDepthParam = 'AvgSBEDropTSDepth'
            avgTempParam = 'AvgSBEDropTSTemp'
        elif (locationName == 'DropcamSBE'):
            avgDepthParam = 'AvgSBEDropcamDepth'
            avgTempParam = 'AvgSBEDropcamTemp'
        else:
            #  we don't compute averages for this mounting location
            avgDepthParam = None
            avgTempParam = None

        return (avgDepthParam, avgTempParam)


    def computeAverages(self):
        """
        computeAverages is called after download to compute the average temp and depth of
        the SBE between EQ and Haulback. These values are then inserted into the EVENT_DATA
        table
        """

        #  7-26-18 - RHT: In addition to tracking the mounting location, I have changed
        #  the event_parameters for the averages so they are specific to the mounting
        #  location. I have omitted computing averages for Camtrawl and "Other" for now.

        #  set the event_parameters based on the mountng location
        avgDepthParam, avgTempParam = self.getAveragesParamNames(self.sbeLocation)
        if (avgDepthParam is None):
            #  we don't compute averages for this mounting location
            return

        ship=self.shipLabel.text()
        survey=self.surveyLabel.text()
        haul=self.haulLabel.text()
        p='Codend'
        avgTemp = float('nan')
        avgDepth = float('nan')

        # Find EQ time
        query=self.db.dbQuery("SELECT parameter_value FROM event_data WHERE ship=" +
                              ship + " AND survey=" + survey + " AND event_id= " +
                              haul + " AND partition='" + p+
                              "' AND event_parameter = 'EQ'")
        eqTime=query.first()

        # Find HB time
        query=self.db.dbQuery("SELECT parameter_value FROM event_data WHERE ship=" +
                              ship + " AND survey=" + survey + " AND event_id= " +
                              haul + " AND partition='" + p+
                              "' AND event_parameter = 'Haulback'")
        hbTime=query.first()

        # Find temperature data between EQ & HB and average
        query=self.db.dbQuery("Select measurement_value FROM event_stream_data WHERE"+
                        " time_stamp between to_timestamp('"+eqTime[0]+"','MMDDYYYY HH24:MI:SS.FF3')" +
                        " and to_timestamp('"+hbTime[0]+"','MMDDYYYY HH24:MI:SS:FF3') AND " +
                        " device_id=" + self.device_id + " AND measurement_type='SBETemperature'")
        
        query_val =query.first()
        if query_val:
            cumVal = 0.
            nVals = 0
            for val, in query:
                cumVal = cumVal + float(val)
                nVals = nVals + 1
            if nVals > 0:
                avgTemp = cumVal / nVals

        # Find depth data between EQ & HB and average
        query=self.db.dbQuery("Select measurement_value FROM event_stream_data WHERE"+
                        " time_stamp between to_timestamp('"+eqTime[0]+"','MMDDYYYY HH24:MI:SS.FF3')" +
                        " and to_timestamp('"+hbTime[0]+"','MMDDYYYY HH24:MI:SS:FF3') AND " +
                        " device_id=" + self.device_id + " AND measurement_type='SBEDepth'")

        if query.first():
            cumVal = 0.
            nVals = 0
            for val, in query:
                cumVal = cumVal + float(val)
                nVals = nVals + 1
            if nVals > 0:
                avgDepth = cumVal / nVals

        # Insert averages into event_data table
        if str(avgTemp)<>'nan':
            self.db.dbQuery("INSERT INTO event_data (ship, survey, event_id, partition, " +
                    "event_parameter, parameter_value) VALUES("+ ship+","+survey+","+haul+",'"+
                    p+"','" + avgTempParam + "',"+str(avgTemp)+")")

            self.db.dbQuery("INSERT INTO event_data (ship, survey, event_id, partition, " +
                    "event_parameter, parameter_value) VALUES("+ship+","+survey+","+haul+",'"+
                    p+"','" + avgDepthParam + "',"+str(avgDepth)+")")
        else:
            #  unable to calculate averages
            QMessageBox.warning(self, 'Attention!', "Unable to calculate averages between EQ and " +
                    "Haulback. Either EQ and HB times are not defined for this event or the timespan " +
                    "of the SBE data does not overlap with EQ and Haulback. That would be bad...")


    def checkPath(self, path, default):
        """
        checkPath cleans up a path and ensures that it has a trailing separator
        and then checks that it exists.
        """

        #  set the default path
        defaultPath =  '.' + os.sep + default + os.sep

        if path <> None:
            #  path provided - normalize the path
            path = os.path.normpath(str(path))

            #  make sure there is a trailing slash
            if (path[-1] <> '/') or (path[-1] <> '\\'):
                path = path + os.sep
        else:
            path = defaultPath

        #  check for the existence of one of our paths
        if not QDir().exists(path):
            if not QDir().exists(defaultPath):
                return (path, False)
            else:
                return (defaultPath, True)
        else:
            return (path, True)


if __name__ == "__main__":

    #  see if the ini file path was passed in
    if (len(sys.argv) > 1):
        iniFile = sys.argv[1]
        iniFile = os.path.normpath(iniFile)
    else:
        #  no argument provided, use default
        iniFile = 'clams.ini'

    #  create an instance of QSettings to load fundamental CLAMS settings
    initSettings = QSettings(iniFile, QSettings.IniFormat)

    #  extract connection parameters
    dataSource = str(initSettings.value('ODBC_Data_Source', 'NULL').toString())
    user = str(initSettings.value('User', 'NULL').toString())
    password = str(initSettings.value('Password', 'NULL').toString())
    schema = str(initSettings.value('Schema', 'NULL').toString())

    #  create an instance of QApplication, our form, and then start
    app = QApplication(sys.argv)
    form = CLAMSsbeDownloader(dataSource, schema, user, password)
    form.show()
    app.exec_()
