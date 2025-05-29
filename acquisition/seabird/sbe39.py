"""

sbe39 is a class that provides an interface for interacting with the Sea-Bird SBE-39
bathythermograph. This class provides methods for the most common commands used with
the SBE 39.

This class supports the SBE39Plus when it is configured in -> legacy <- mode.


Notes:

BINARY DOWNLOADING HAS NOT BEEN IMPLEMENTED

The connect method will wake the SBE which stops logging (and real-time output) if
the sampling interval is >= 3.

When the SBE's sampling interval is set >= 3 you will see a couple of chars of
gibberish after each line in the real-time output. This comes from the serial
driver in the SBE as it shuts down. You can ignore this.

Also, when the SBE's sampling interval is set >= 3 and you "wake" the device and get the
command prompt, it will not display or record any more data until the SBE times out or is
forced back to sleep.

When issuing the "StartNow" command and interval is set >= 3 the device will start logging
and then go to sleep. If you send any commands to the SBE after issuing "startnow" the
device will be woken up and will not record data until the connection times out.

This class tries to track the connection state (sleep vs awake) and will wake devices it
thinks are sleeping. It will only do this on demand so if you sleep a device (either
explicitly or implicitly) it will stay asleep until you issue another command.

IF YOU HAVE VERY LONG SAMPLING INTERVALS YOU WILL NEED TO MODIFY __maxConAttempts SO THAT
THIS CLASS WILL KEEP TRYING TO WAKE THE DEVICE FOR A PERIOD LONGER THAN THE SAMPLING INTERVAL.
This should be handled better but for now this is how it is.

"""

import datetime
import struct
from PyQt6.QtCore import *
from acquisition.SensorMonitor import SensorMonitor


class sbe39(QObject):
    """A class for downloading data from and setting parameters on the Sea Bird SBE 39 bathythermograph
    """

    #  define the sbe39 class's signals
    SBETimeout = pyqtSignal(str)
    SBEData = pyqtSignal(str, str)
    SBEConnected = pyqtSignal(str)
    SBEDownloadData = pyqtSignal(str, list)
    SBEProgress = pyqtSignal(str, float)
    SBEAbort = pyqtSignal(str)
    SBEStatus = pyqtSignal(str, dict)
    SBECalibration = pyqtSignal(str, dict)
    SBEDownloadComplete = pyqtSignal(str, int, int)
    SBETimeout = pyqtSignal(str)

    def __init__(self, serialPort, deviceName='SBE39', baud=9600, serialMonitor=None, parent=None):
        #  initialize the parent
        QObject.__init__(self, parent)

        #  set some internal parms
        self.deviceName = deviceName
        self.rxBuffer = []
        self.txBuffer = []
        self.status = {}
        self.calibration = {}
        self.connected = False
        self.sbeIsAsleep = False
        self.binaryUploadEnable = True
        self.isAborting = False
        self.justStarted = False
        self.nTotalRecords = 0
        self.CTS = True
        self.nRecDL = 0
        self.maxConAttempts = 200
        self.extraSleepy = 0
        self.lastCommand = ''

        #  check if we're using an existing serial monitor or creating a new one
        if (serialMonitor == None):
            #  create a new instance of the serial monitor
            self.serMonitor = SensorMonitor.SensorMonitor()
        else:
            #  use an existing instance
            self.serMonitor = serialMonitor

        #  connect to the serial monitor's "SensorDataReceived" signal
        self.serMonitor.SensorDataReceived.connect(self.rxData)

        #  add this device to the serial monitor
        self.serMonitor.addDevice(deviceName, serialPort, baud, 'None', '', 0,
                                  cmdPrompt='S>', pollRate=1000)

        #  set a timer to handle the connection state and transmitting of data.
        #  do not alter the timing of this timer since it will affect the timing
        #  of the command response processing.
        self.txTimer = QTimer(self)
        self.txTimer.setSingleShot(False)
        self.txTimer.setInterval(100)
        self.txTimer.timeout.connect(self.pollTxBuffer)

        #  set up a timeout timer to handle breakdowns in communication with SBE.
        #  There are 2 ways we can time out talking to the SBE. The first is when
        #  we're trying to connect/wake up an SBE. Those timeouts are handled in
        #  pollTxBuffer. The second way we timeout is when we start to talk to
        #  the SBE and it just stops (like when the battery dies). This timer
        #  handles this second case by starting when a command is sent, reseting
        #  when data is received, and stopping when a command/response sequence
        #  is finished. If the timeout method is called we assume that we have
        #  lost the connection to the SBE because we sent it a command and we
        #  never received the full response.
        self.rxTimeoutTimer = QTimer(self)
        self.rxTimeoutTimer.setSingleShot(True)
        self.rxTimeoutTimer.setInterval(3000)
        self.rxTimeoutTimer.timeout.connect(self.rxTimeout)


    def setConnectionParams(self, serialPort, baud):
        """setConnectionParams sets the serial port parameters used to communicate with
        the SBE. These can only be changed if we're not currently connected to the SBE.
        """
        if (not self.connected):
            #  first remove the existing serial monitor entry for this device
            self.serMonitor.removeDevice(self.deviceName)

            #  now add this device to the serial monitor woth the new parameters
            self.serMonitor.addDevice(self.deviceName, serialPort, baud, 'None', '', 0,
                                      cmdPrompt='S>', pollRate=1000)


    def connect(self):
        """ connect opens the serial connection and wakes the SBE device.  If the connection
        succeeds you will receive the "SBEConnected" signal. If the connection fails you
        will either receive an "SBETimeout" signal or an exception will be raised if the
        serial port cannot be opened.

        Once connected the SBE will be kept awake so do not leave the SBE connected longer
        than is required to save battery power.

        You must call connect before you call any of the other methods.
        """

        if (not self.connected):

            try:
                #  start monitoring this device
                self.serMonitor.startMonitoring(devices=[self.deviceName])

                #  set some state variables
                self.connected = True
                self.isConnecting = True

                #  assume the device is asleep and reset the wake attempts
                self.sbeIsAsleep = True
                self.attempts = 0

                #  try to wake the device
                self.txCommand([''])

                #  start the tx processing timer
                self.txTimer.start()

                #  the rest of the connect logic is handled in pollTxBuffer and rxData

            except Exception as e:
                #  there was a problem with the serial connection
                raise e


    def getStatus(self):
        """getStatus gets the current status of the SBE. Note that you must connect the SBEStatus
        signal so you are informed when the status data has been received and processed.
        """

        if (self.connected):
            #  send the get status command
            self.txCommand(['DS'])


    def setTxRealTime(self, state):
        """setTxRealTime sets the real time output state. Set to True to enable real-time output
        and False to disable it.
        """

        if (self.connected):
            if (state):
                state = 'Y'
            else:
                state = 'N'

            #  send the tx real-time command
            self.txCommand(['TXREALTIME=' + state])


    def setSamplingInterval(self, num):
        """setSamplingInterval sets the interval (in seconds) between samples. Valid values are:
            0 = continuous (actual interval is between ~0.8s and ~1.5s depending configuration)
            3-32767 = sampling at the interval specified. The device sleeps between intervals.

            Note that values less than 3 will be set to 0 and result in continuous sampling.
        """

        if (self.connected):
            #  clamp values to a valid range and convert number to an integer string
            if (num < 3):
                num = 0
            elif (num > 32767):
                num = 32767
            num = str(int(num))

            #  send the interval command
            self.txCommand(['INTERVAL=' + num])


    def setBaud(self, baud):
        """setBaud sets the serial baud rate of the device. Valid values are 1200,
        2400, 4800, 9600, 19200, and 38400. The default SBE baud rate is 9600. Make
        sure you know what you're doing and know how to get the SBE back to a known
        baud if you're messing with this.
        """

        if (self.connected):
            validRates = [1200, 2400, 4800, 9600, 19200, 38400]
            try:
                #  check that the supplied rate is a valid one
                validRates.index(baud)

                #  send the set baud command
                self.txCommand(['BAUD=' + str(baud)])
            except:
                #  the suppllied rate is not in the list of valid rates
                raise SBEError('Invalid baud rate: ' + str(baud) + '.')


    def setSampleNumber(self, num):
        """setSampleNumber sets the sample number where the logger will begin to store data.
        Typically you set the sample number to 0 when preparing an SBE for deployment.
        This method will stop the logger.
        """

        if (self.connected):

            #  Stop logging
            self.stop()

            #  convert our input number to an integer string
            num = str(int(num))

            #  send the set sample number command
            self.txCommand(['SAMPLENUM=' + num])

            #  for SBE38Plus we have to resend the same command to confirm
            #  so we store it here to send when requested.
            self.lastCommand = 'SAMPLENUM=' + num


    def sleep(self):
        """sleep sleeps the SBE. DO NOT SLEEP THE DEVICE IF THE SAMPLING INTERVAL IS 0 AND
        YOU HAVE ISSUED A STARTNOW COMMAND. If you do so, the device will stop logging. You
        can (and probably should) sleep a device that you have configured to start at a
        later time.
        """

        if (self.connected):
            #  send the get status command
            self.txCommand(['QS'])


    def getCalParms(self):
        """getCalParms gets the calibration parameters from the SBE and stores them in
        the calibration property. Note that you need to connect the SBECalibration signal
        to know when these parameters have been received.
        """

        if (self.connected):
            #  send the DC command
            self.txCommand(['DC'])


    def disconnect(self):
        """disconnect closes down the connection to the SBE.
        """

        if (self.connected):

            #  stop monitoring the SBE (this closes the serial port)
            self.serMonitor.stopMonitoring(devices=[self.deviceName])

            #  stop the timers
            self.txTimer.stop()
            self.rxTimeoutTimer.stop()

            #  reset internal properties
            self.connected = False
            self.calibration = {}
            self.status = {}
            self.rxBuffer = []
            self.txBuffer = []


    def stop(self):
        """stop stops logging data. It also cancels a startLater command.
        """

        if (self.connected):
            #  send the stop logging command
            self.txCommand(['STOP'])


    def startNow(self):
        """startNow starts the SBE logging immediately. Note that after starting logging
        do not sleep the device!
        """

        if (self.connected):
            #  send the start logging now command. The startnow command will put the SBE
            #  to sleep if the interval > 0 so we need to set dconCmd = True.
            self.txCommand(['STARTNOW'])


    def startLater(self):
        """startLater initiates delayed logging. Logging will start when the delayed start
        date and time is reached. You need to set the delayed start date and time prior
        to issuing this command.
        """

        if (self.connected):
            #  send the start logging now command
            self.txCommand(['STARTLATER'])


    def setStartDateTime(self, time=None, delay=None, localTime=False):
        """setStartDateTime sets the delayed start date and time by sending both the
        StartDDMMYY and StartHHMMSS commands to the SBE. You can specify the delayed
        start date and time in a couple of ways:

        Setting time to an instance of a python datetime object will set the start date
        and time in the SBE to the date and time of the datetime object. The delay and
        localTime arguments are ignored.

        If you do not set time, you can set delay to a float specifying the number of
        minutes into the future (as determined from the current PC time) the SBE start
        date and time should be set to. Set localTime to true to if you have set the
        SBE's RTC to use local time.

        It is your responsibility to set the RTC and the start date and times to sane
        values. It is your problem if you say set the internal clock to UTC and your
        start time to local time.
        """

        if (self.connected):

            #  if time is not passed use the current time
            if (time == None):
                #  get the current time
                if (localTime):
                    #  get the local time
                    time = datetime.datetime.now()
                else:
                    #  get UTC time
                    time = datetime.datetime.utcnow()

                if delay:
                    #  apply delay if provided
                    time = time + datetime.timedelta(minutes=delay)

            #  transmit the commands
            self.txCommand(self.formatTime(time, start=True))


    def download(self, start=1, stop=None, mode='ASCII'):
        """download downloads data from the SBE. If called with no parameters it will
        download all samples from the first to the current sample at the time of the
        last status update. Specify the start and stop samples if you want a different
        behavior.

        Note that it seems that the last few samples downloaded are bogus. Not really
        sure what causes this but if you call download with no arguments I subtract 4
        samples from the current sample number to avoid these bad samples. This
        shouldn't cause any problems but be aware of this feature. If you explicitly set
        the stop sample number it will not be molested.

                     CURRENTLY BINARY DOWNLOAD IS NOT IMPLEMENTED.
        """

        if (self.connected):

            #  force ASCII download since binary download isn't implemented
            mode='ascii'

            if (stop):
                #  stop sample provided - use that
                stop = int(stop)
            else:
                #  stop sample not provided - get it from status
                stop = int(self.status['sample number'])
                #  subtract 4 from the stop sample number to skip the few bogus
                #  samples at the end of the download.
                if (stop > 5):
                    stop = stop - 4

            #  initialize some variables
            self.dlProgress = 0
            self.nRecDL = 0

            #  force ASCII upload if binary upload isn't available.
            if (self.binaryUploadEnable == False):
                mode='ASCII'

            #  determine the total records to download
            self.nTotalRecords = (stop - start) + 1

            #  convert our input numbers to an integer strings
            start = str(int(start))
            stop = str(int(stop))

            if (mode.lower() == 'ascii'):
                #  send the download ASCII command
                self.txCommand(['DD' + start + ',' + stop])
            else:
                #  set binary time to on
                self.setBinaryTime(True)

                #  send the download binary command
                self.txCommand(['DB' + start + ',' + stop])


    def abort(self):
        """abort aborts the download in progress

        THIS DOES NOT SEEM TO WORK WITH SBE39+ devices. I don't currently know how
        to stop SBE39+ units when they are downloading data.

        """
        self.isAborting = True
        #  send the <ctrl>+c directly to avoid serialization by txCommand
        self.serMonitor.txData(self.deviceName, '\x03\r')


    def setBinaryTime(self, state):
        """setBinaryTime configures the SBE to either output time with every record during
        a binary download (set state to True) or it configures the SBE to only output
        time for the first record.
        """

        if (self.connected):
            if (state):
                state = 'Y'
            else:
                state = 'N'

            #  send the stop logging command
            self.txCommand(['BINARYTIME=' + state])


    def setRTC(self, time=None, localTime=False):
        """setRTC sets the internal real-time clock. This should be done when preparing the
        SBE for deployment. To set the internal clock to the current time in GMT pass no
        arguments. If you want to set the time to *LOCAL* time, set localTime to True. If you
        want to set the time to something else, set time to an instance of a datetime object
        configured as you see fit.

            NOTE: THIS METHOD STOPS LOGGING BEFORE SETTING THE CLOCK.

        """

        if (self.connected):
            #  stop the device
            self.stop()

            #  if time is not passed use the current time
            if (time == None):
                #  get the current time
                if (localTime):
                    #  get the local time
                    time = datetime.datetime.now()
                else:
                    #  get UTC time
                    time = datetime.datetime.utcnow()

            #  transmit the commands
            self.txCommand(self.formatTime(time))


    def txCommand(self, cmdList):
        '''
        txCommand appends the list of commands to the command queue. Commands are issued
        serially. The next command in the queue is not sent until the previous command
        has completed.
        '''
        #  add the command(s) to the transmit buffer and append <cr>.
        for cmd in cmdList:
            self.txBuffer.append(cmd + '\r')


    def pollTxBuffer(self):
        '''pollTxBuffer checks the transmit buffer and the state of the connection
        to the SBE and either attempts to wake the SBE or send it a command. This
        method is called by the
        '''

        if (self.connected) and (len(self.txBuffer) > 0):
            if (self.sbeIsAsleep == True):
                #  the SBE is sleeping (or so we think) so we send <cr>'s until it responds
                if (self.attempts < self.maxConAttempts):
                    #  still trying to wake up the SBE... transmit the <cr> to try to wake the unit
                    self.serMonitor.txData(self.deviceName, '\r')
                    self.attempts = self.attempts + 1
                else:
                    #  we're giving up - emit timeout signal and disconnect
                    self.disconnect()
                    self.SBETimeout.emit(self.deviceName)

            else:
                #  the SBE is awake - check if we have anything in the buffer
                #  and if we're ready to tx another command
                if (self.CTS == True):
                    #  pop the next command off the stack and send.
                    cmd = self.txBuffer.pop(0)

                    #  Tx the command
                    self.serMonitor.txData(self.deviceName, cmd)

                    #  update lastCommand
                    self.lastCommand = cmd

                    #  QS is a special case that immediately puts the device to sleep such
                    #  that no further data is received. So if we've just issued the
                    #  QS command we'll update the connection state variables here.
                    if (cmd == 'QS'):
                        self.sbeIsAsleep = True
                        self.extraSleepy = 0
                        self.attempts = 0

                    #  set clear to send to false
                    self.CTS = False

                    #  start the rxTimeout timer
                    self.rxTimeoutTimer.start()


    def rxData(self, name, val, err):
        '''rxData is an internal method that processes the lines of data received from
        the SBE device. Commands are sent and procesed serially and this method maintains the
        current connection state in lastCommand. When lastCommand = '' we're not in a
        command/response sequence. Otherwise lastCommand contains the command string of the
        command it is in the process of handling.
        '''

        #  Filter errors
        #
        #  There are some errors we don't care about. For example, if we issue a STOP
        #  command when the device is already stopped. The SBE38plus will issue an error
        #  message and we want to ignore it.

        #  Filter the inactive command error issued after the stop command when the
        #  device is already stopped.
        if (self.lastCommand.lower().find('stop') > -1) and (val.lower().find('inactive command') > -1):
            return

        #  emit a signal containing the SBE serial data. You can use this to show
        #  or record "live" data from the device.
        if val:
            self.SBEData.emit(self.deviceName, val)

        #  swallow the first "S>" if we (may) have just started the SBE. Some units send one
        #  more "S>" after starting and some do not.
        if (val == 'S>') and (self.justStarted):
            self.justStarted = False
            val = ''

        #  if we're in the process of connecting or waking the device and we receive
        #  the command prompt we've woken the sbe (or so we think).
        if (self.sbeIsAsleep == True) and (val == 'S>'):
            #  older devices don't always respond after the first S> so we wait for 3
            if (self.extraSleepy == 3):
                #  we've finished the connecting/reconnecting process
                self.sbeIsAsleep = False
                self.extraSleepy = 0
                #  emit the SBEConnected signal if this is the first time we are connecting
                if (self.isConnecting == True):
                    self.SBEConnected.emit(self.deviceName)
                    self.isConnecting = False
            else:
                #  increment our extra-sleepy counter
                self.extraSleepy = self.extraSleepy + 1

        #  ignore real-time output data from this point on
        if val.lower().find('<datapacket>') > -1: # or <insert SBE39 RT output handling here>
            return

        if (self.CTS == False):
            #  restart our rxTimeout timer since we've received data and we're in a
            #  command/response sequence. If we're simply rx'ing data because real-time
            #  output is enabled we don't want to start the timer.
            self.rxTimeoutTimer.start()

        #  if we're in the *middle* of processing a response, handle it here.
        if ((self.lastCommand.lower().find('ds') == 0) or
                (self.lastCommand.lower().find('dc') == 0) or
                (self.lastCommand.lower().find('*db') == 0)):

            #  we're processing a response that doesn't require progress tracking
            self.rxBuffer.append(val)

        elif (self.lastCommand.lower().find('dd') == 0) or (self.lastCommand.lower().find('db') == 0):
            #  currently processing a response that requires progress tracking

            if (self.lastCommand.lower().find('db') == 0):
                #  check if we've rx'd the final line of data
                if (val[-2:] == 'S>'):
                    #  store the data from the last line then strip the command prompt
                    self.rxBuffer.append(val[:-2])
                    val = val[-2:]
                else:
                    #  no command prompt sent - just append data
                    self.rxBuffer.append(val)
            else:
                #  parse and store ASCII data
                if (val != 'S>'):
                    parts = val.split(',')
                    #  check that this is a valid line of data (4 values)
                    if (len(parts) == 4):
                        try:
                            #  attempt to convert values
                            time = datetime.datetime.strptime(parts[2].strip() + parts[3], '%d %b %Y %H:%M:%S')
                            temp = float(parts[0])
                            pressure = float(parts[1])

                            #  increment our record counter
                            self.nRecDL = self.nRecDL + 1.

                            #  emit a signal containing this line of data
                            self.SBEDownloadData.emit(self.deviceName, [time, temp, pressure])

                            #  calculate progress and emit signal if changed
                            dlProgress = (self.nRecDL /self.nTotalRecords) * 100.
                            if (dlProgress != self.dlProgress):
                                self.dlProgress = dlProgress
                                self.SBEProgress.emit(self.deviceName, self.dlProgress)

                        except:
                            #  conversion failed - bad/garbled data - ignore this line
                            pass

        #  check if we've rx'd the command prompt which indicates the end of a command/response sequence.
        if (val == 'S>'):
            #  our next step depends on what the command was...
            if (self.isAborting):
                #  we were told to abort a download
                self.isAborting = False
                self.SBEAbort.emit(self.deviceName)

            elif self.lastCommand.lower().find('ds') == 0:
                #  we've rx'd the entire status message - process it
                self.processStatus()

                #  emit status signal
                self.SBEStatus.emit(self.deviceName, self.status)

            elif self.lastCommand.lower().find('*db') == 0:
                #  we've rx'd the entire binary parameters message - process it
                self.processBinParms()

                #  NEED TO ADD A SIGNAL HERE OR WILL WE JUST USE THIS INTERNALLY?

            elif self.lastCommand.lower().find('dc') == 0:
                #  we've rx'd the entire cal parms message - process it
                self.processCalParms()

                #  else emit calibration signal
                self.SBECalibration.emit(self.deviceName, self.calibration)

            elif self.lastCommand.lower().find('db') == 0:
                #  we've rx'd the entire binary download - what do we do now?

                #  binary unpacking is not implemented.
                print(len(self.rxBuffer))
                for line in self.rxBuffer:
                    print(struct.unpack_from('f', line))

            elif self.lastCommand.lower().find('dd') == 0:
                #  we've rx'd the entire ASCII download - emit a download complete message

                #  calculate the number of dropped samples
                nDropped = self.nTotalRecords - self.nRecDL

                #  stop the timer in case the application pauses handling the SBEDownloadComplete signal
                self.rxTimeoutTimer.stop()

                #  emit a signal to inform listeners that we're done downloading
                self.SBEDownloadComplete.emit(self.deviceName, self.nRecDL, nDropped)

            #  we are done processing the last request
            self.lastCommand = ''
            self.CTS = True
            self.rxTimeoutTimer.stop()


        #  Now we handle the special cases...
        elif (val.lower().find('startnow') > -1) or (val.lower().find('start now') > -1):
            #  the startnow command will put the SBE to sleep if interval>0 right after it
            #  sends out the "start now" response signaling that the command completed
            #  successfully. When this happens we need to update the connection state so
            #  we wake the device the next time we interact with it.
            self.sbeIsAsleep = True
            self.extraSleepy = 0
            self.attempts = 0
            self.CTS = True
            self.rxTimeoutTimer.stop()
            #  lastly we need to set the justStarted property since some versions of the
            #  firmware spit out one more "S>" after starting and then go to sleep so we
            #  need to swallow the next "S>" we see. Not ideal but...
            self.justStarted = True

        #  the SBE39Plus requires certain commands to be entered twice to confirm intent
        #  An example is the SAMPLENUM command.
        elif val.find('<!--Repeat command') > -1:
            #  need to send the repeated command directly since there may
            #  be other commands in the queue
            self.serMonitor.txData(self.deviceName, self.lastCommand + '\r')

        elif val.lower().find('timeout') > -1:
            #  the last thing we check is if we're timed out due to inactivity. If the SBE
            # has timed out and gone to sleep we update connection state variables
            self.sbeIsAsleep = True
            self.attempts = 0


    def processBinParms(self):
        """processBinParms extracts the binary download parameters.

        This is untested.
        """

        #  reset the calibration parameters dict
        self.binDownloadParms = []

        #  work thru each line in the buffer and process
        for line in self.rxBuffer:
            #  make sure we're parsing a parameter line and not a data line
            if (line.find(',') > -1) and (line.find(':') == -1):
                #  process the binary download parameters
                tempVals = line.split(',')
                for i in tempVals:
                    self.binDownloadParms = float(i)

        self.rxBuffer = []


    def processCalParms(self):
        """processCalParms extracts the temp and pressure calibration parameters
        from the data received from the "dc" command and inserts it into a dict.
        """

        #  reset the calibration parameters dict
        self.calibration = {}

        #  work thru each line in the buffer and process
        for line in self.rxBuffer:

            if (line.lower().find('temperature') > -1):
                #  process the temp sensor cal date
                self.calibration['temp cal date'] = line.split(':')[1].strip()

            elif (line.find('TA0') > -1):
                #  process TA0 parm
                self.calibration['TA0'] = float(line.split('=')[1].strip())

            elif (line.find('TA1') > -1):
                #  process TA1 parm
                self.calibration['TA1'] = float(line.split('=')[1].strip())

            elif (line.find('TA2') > -1):
                #  process TA2 parm
                self.calibration['TA2'] = float(line.split('=')[1].strip())

            elif (line.find('TA3') > -1):
                #  process TA3 parm
                self.calibration['TA3'] = float(line.split('=')[1].strip())

            elif (line.lower().find('pressure') > -1):
                #  process the presssure sensor cal date
                line = line.split(',')
                self.calibration['pressure s/n'] = line[0].split('S/N')[1].strip()
                if line[1].find(':') < 0:
                    line = line[1].split('  ')
                else:
                    line = line[1].split(':')
                self.calibration['pressure range'] = line[0].split('=')[1].strip()
                self.calibration['pressure cal date'] = line[1].strip()

            elif (line.find('PA0') > -1):
                #  process PA0 parm
                self.calibration['PA0'] = float(line.split('=')[1].strip())

            elif (line.find('PA1') > -1):
                #  process PA1 parm
                self.calibration['PA1'] = float(line.split('=')[1].strip())

            elif (line.find('PA2') > -1):
                #  process PA2 parm
                self.calibration['PA2'] = float(line.split('=')[1].strip())

            elif (line.find('PTHA0') > -1):
                #  process PTHA0 parm
                self.calibration['PTHA0'] = float(line.split('=')[1].strip())

            elif (line.find('PTHA1') > -1):
                #  process PTHA1 parm
                self.calibration['PTHA1'] = float(line.split('=')[1].strip())

            elif (line.find('PTHA2') > -1):
                #  process PTHA2 parm
                self.calibration['PTHA2'] = float(line.split('=')[1].strip())

            elif (line.find('PTCA0') > -1):
                #  process PTCA0 parm
                self.calibration['PTCA0'] = float(line.split('=')[1].strip())

            elif (line.find('PTCA1') > -1):
                #  process PTCA1 parm
                self.calibration['PTCA1'] = float(line.split('=')[1].strip())

            elif (line.find('PTCA2') > -1):
                #  process PTCA2 parm
                self.calibration['PTCA2'] = float(line.split('=')[1].strip())

            elif (line.find('PTCB0') > -1):
                #  process PTCB0 parm
                self.calibration['PTCB0'] = float(line.split('=')[1].strip())

            elif (line.find('PTCB1') > -1):
                #  process PTCB1 parm
                self.calibration['PTCB1'] = float(line.split('=')[1].strip())

            elif (line.find('PTCB2') > -1):
                #  process PTCB2 parm
                self.calibration['PTCB2'] = float(line.split('=')[1].strip())

        #  clear out the buffer
        self.rxBuffer = []


    def processStatus(self):
        """processStatus extracts the status information received from the "ds"
        command and inserts it into a dict.
        """

        #  reset the status parameters dict
        self.status = {}

        #  work thru each line in the buffer and process
        for line in self.rxBuffer:

            if (line.lower().find('serial no') > -1):
                #  process the status header
                line = line.split('  ')

                # the SBE39 uses 'V' for the version char and SBE39Plus uses 'v'
                if 'V' in line[0]:
                    verChar = 'V'
                else:
                    verChar = 'v'
                self.status['device'] = line[0].split(verChar)[0].strip()
                self.status['version'] = line[0].split(verChar)[1].strip()
                ver_bits = self.status['version'].split('.')
                try:
                    self.status['version_numeric'] = float(ver_bits[0] + '.' + ver_bits[1])
                except:
                    self.status['version_numeric'] = 0
                if self.status['version_numeric'] < 1.7:
                    self.binaryUploadEnable = False
                self.status['serial number'] = line[1].split('.')[1].strip()
                if verChar == 'V':
                    #  the SBE39's time string ends up being split above - we join it here before parsing.
                    timeStr = ' '.join(line[3:5]).strip()
                    self.status['time'] = datetime.datetime.strptime(timeStr, '%d %b %Y %H:%M:%S')
                else:
                    #  this is an SBE39Plus which doesn't have a split time string
                    self.status['time'] = datetime.datetime.strptime(line[2].strip(), '%d %b %Y %H:%M:%S')

            elif (line.lower().find('volt') > -1):
                #  process the battery voltage

                #  first check for low battery warning
                if line.lower().find('low battery') > -1:
                    self.lowBattery = True
                    continue

                #  this is not the low battery warning, so assume this is the voltage status
                volt_parts = line.split(',')
                self.status['voltage'] = volt_parts[0].split('=')[1].strip()
                if len(volt_parts) > 1:
                    self.status['backup_voltage'] = volt_parts[1].split('=')[1].strip()

            elif (line.lower().find('logging') > -1):
                #  process logging status
                if (line.lower().find('not') > -1):
                    self.status['logging status'] = 'not logging'
                else:
                    self.status['logging status'] = 'logging'

            elif (line.lower().find('interval') > -1):
                #  process sample interval
                self.status['sample interval'] = line.split('=')[1].strip()

            elif (line.lower().find('samplenumber') > -1):
                #  process sample number
                line = line.split(',')
                self.status['sample number'] = line[0].split('=')[1].strip()
                self.status['sample free'] = line[1].split('=')[1].strip()

            elif (line.lower().find('sync') > -1):
                #  process serial sync
                self.status['serial sync'] = line.split('mode')[1].strip()

            elif (line.lower().find('output') > -1):
                #  process real-time output
                self.status['real-time output'] = line.split('output')[1].strip()

            elif (line.lower().find('configuration') > -1):
                #  process configuration
                self.status['configuration'] = line.split('=')[1].strip()

            elif (line.lower().find('upload') > -1):
                #  process binary upload config
                self.status['binary upload config'] = line.split('upload')[1].strip()

            elif (line.lower().find('temperature') > -1):
                 #  process configuration
                self.status['temperature'] = line.split('=')[1].strip().split(' ')[0]

        #  clear out the buffer
        self.rxBuffer = []


    def rxTimeout(self):
        '''rxTimeout is called when we time out in the middle of a command/response sequence.
        If we time out we assume that we've lost the connection to the SBE and we disconnect.
        '''
        self.disconnect()
        self.SBETimeout.emit(self.deviceName)


    def __del__(self):
        """__del__ is called when the object is deleted. We just make sure we've cleaned up...
        """
        if (self.connected):
            #  stop monitoring the SBE (this closes the serial port)
            self.serMonitor.stopMonitoring(devices=[self.deviceName])


    def formatTime(self, time, start=False):
        """Internal function to return formatted time strings suitable for the SBE39. This
        method formats both the values for setting the RTC and for setting the delayed
        start times.
        """
        #  construct the two time strings
        mdy = 'mmddyy={:02d}{:02d}'.format(time.month, time.day) + str(time.year)[2:4]
        hms = 'hhmmss={:02d}{:02d}{:02d}'.format(time.hour, time.minute, time.second +
                                                 int(round(time.microsecond/1000000.)))

        #  if the "start" keyword is set we format the text for the start later commands
        if (start):
            mdy = 'START' + mdy
            hms = 'START' + hms

        return [mdy,hms]


class SBEError(Exception):
    def __init__(self, msg, parent=None):
        self.errText = msg
        self.parent = parent

    def __str__(self):
        return repr(self.errText)
