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
import re
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
        self.lowBattery = False
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
        if serialMonitor is None:
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
        if self.connected:
            # Use GetSD or GetHD for SBE39plus native mode
            self.txCommand(['GetSD'])


    def setTxRealTime(self, state):
        """setTxRealTime sets the real time output state. Set to True to enable real-time output
        and False to disable it.
        """
        if self.connected:
            state_str = 'Y' if state else 'N'

            # Send Native SBE 39plus command (OutputRealTime=Y/N)
            # Note: If running older/legacy firmware, use 'TXREALTIME=' instead.
            self.txCommand([f'OutputRealTime={state_str}'])


    def setSamplingInterval(self, num):
        """setSamplingInterval sets the interval (in seconds) between samples. Valid values are:
            0 = continuous (actual interval is between ~0.8s and ~1.5s depending configuration)
            3-32767 = sampling at the interval specified. The device sleeps between intervals.

            Note that values less than 3 will be set to 0 and result in continuous sampling.
        """
        if self.connected:
            # Clamp values to valid integer range (0 to 32767)
            num = int(num)
            if num < 0:
                num = 0
            elif num > 32767:
                num = 32767

            # Send Native SBE 39plus command (SampleInterval=x)
            self.txCommand([f'SampleInterval={num}'])


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
        if self.connected:
            self.txCommand(['GetCC'])


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
        if self.connected:
            if time is None:
                if localTime:
                    time = datetime.datetime.now()
                else:
                    # Use timezone-aware UTC then convert to naive for formatting
                    time = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            if delay:
                time = time + datetime.timedelta(minutes=delay)

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

        if self.connected:

            # Force ASCII mode (binary unpacking not implemented)
            mode = 'ascii'

            if stop:
                # Stop sample provided - use that
                stop = int(stop)
            else:
                # Stop sample not provided - get it from status dictionary
                stop = int(self.status.get('sample number', 0))
                # Subtract 4 from stop sample to avoid bogus/partial trailing records
                if stop > 5:
                    stop = stop - 4

            # Initialize progress variables
            self.dlProgress = 0
            self.nRecDL = 0

            # Determine total records to download
            self.nTotalRecords = max((stop - int(start)) + 1, 1)

            # Convert input numbers to string formats
            start_str = str(int(start))
            stop_str = str(int(stop))

            # --- THIS IS THE UPDATED COMMAND FOR NATIVE SBE 39plus ---
            # SBE 39plus Native uses 'GetSamples:start,stop' instead of 'DDstart,stop'
            self.txCommand([f'GetSamples:{start_str},{stop_str}'])


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
        if self.connected:
            # Stop logging before setting clock
            self.stop()

            if time is None:
                if localTime:
                    time = datetime.datetime.now()
                else:
                    time = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

            # Transmit the formatted commands
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
        """
        rxData is an internal method that processes the lines of data received from
        the SBE device. Commands are sent and processed serially and this method maintains the
        current connection state in lastCommand. When lastCommand = '' we're not in a
        command/response sequence. Otherwise lastCommand contains the command string of the
        command it is in the process of handling.
        :param name:
        :param val:
        :param err:
        :return:
        """
        # Filter inactive command error issued after the stop command when device is stopped
        if ('stop' in self.lastCommand.lower()) and ('inactive command' in val.lower()):
            return

        # Emit a signal containing raw SBE serial data for live viewing/logging
        if val:
            self.SBEData.emit(self.deviceName, val)

        # Swallow initial "S>" prompt if we just started logging
        if (val == 'S>') and self.justStarted:
            self.justStarted = False
            val = ''

        # Handle connection / wake-up prompt detection (Supports legacy "S>" and native XML prompts)
        if self.sbeIsAsleep and (val == 'S>' or '<ExecCommand' in val):
            self.sbeIsAsleep = False
            self.extraSleepy = 0
            if self.isConnecting:
                self.SBEConnected.emit(self.deviceName)
                self.isConnecting = False

        # Ignore real-time data packet wrappers
        if '<datapacket>' in val.lower():
            return

        # Restart rxTimeoutTimer if receiving data during an active command sequence
        if not self.CTS:
            self.rxTimeoutTimer.start()

        cmd = self.lastCommand.lower().strip()

        # BUFFER METADATA RESPONSES (DS, GETSD, GETHD, DC, GETCC)
        if (cmd.startswith('ds') or cmd.startswith('getsd') or cmd.startswith('gethd') or
                cmd.startswith('dc') or cmd.startswith('getcc') or cmd.startswith('*db')):
            self.rxBuffer.append(val)

        # PARSE DATA DOWNLOAD STREAMS (DD, GETSAMPLES, DB)
        elif cmd.startswith('dd') or cmd.startswith('getsamples') or cmd.startswith('db'):

            if cmd.startswith('db'):
                # Binary download processing
                if val.endswith('S>'):
                    self.rxBuffer.append(val[:-2])
                    val = val[-2:]
                else:
                    self.rxBuffer.append(val)
            else:
                # ASCII download processing (Supports legacy DD comma format & SBE39plus GetSamples stream)
                if val != 'S>' and not val.startswith('</'):
                    # Strip any inline XML tags if present in the data stream
                    clean_val = re.sub(r'<[^>]+>', '', val).strip()
                    if clean_val:
                        parts = [p.strip() for p in clean_val.split(',')]

                        # Native and Legacy ASCII outputs deliver 3 to 4 comma-separated values
                        if len(parts) >= 3:
                            try:
                                temp = float(parts[0])

                                # Determine pressure and datetime format based on array length
                                if len(parts) == 4:
                                    pressure = float(parts[1])
                                    time_str = f"{parts[2]} {parts[3]}"
                                else:
                                    pressure = 0.0
                                    time_str = parts[1] if len(parts) == 2 else f"{parts[1]} {parts[2]}"

                                # Parse datetime string
                                try:
                                    time = datetime.datetime.strptime(time_str, '%d %b %Y %H:%M:%S')
                                except ValueError:
                                    # Try alternative ISO format if SBE39plus outputs YYYY-MM-DDTHH:MM:SS
                                    time = datetime.datetime.strptime(time_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')

                                self.nRecDL += 1.0

                                # Emit downloaded sample signal
                                self.SBEDownloadData.emit(self.deviceName, [time, temp, pressure])

                                # Update download progress
                                if self.nTotalRecords > 0:
                                    dlProgress = (self.nRecDL / self.nTotalRecords) * 100.0
                                    if dlProgress != self.dlProgress:
                                        self.dlProgress = dlProgress
                                        self.SBEProgress.emit(self.deviceName, self.dlProgress)

                            except Exception:
                                # Garbled or header line - swallow and continue
                                pass

        # CHECK FOR COMMAND RESPONSE COMPLETION PROMPTS
        if val == 'S>' or '</StatusData>' in val or '</CalibrationData>' in val or '</HardwareData>' in val:

            if self.isAborting:
                self.isAborting = False
                self.SBEAbort.emit(self.deviceName)

            elif cmd.startswith('ds') or cmd.startswith('getsd') or cmd.startswith('gethd'):
                self.processStatus()
                self.SBEStatus.emit(self.deviceName, self.status)

            elif cmd.startswith('*db'):
                self.processBinParms()

            elif cmd.startswith('dc') or cmd.startswith('getcc'):
                self.processCalParms()
                self.SBECalibration.emit(self.deviceName, self.calibration)

            elif cmd.startswith('db'):
                print(f"Downloaded binary buffer length: {len(self.rxBuffer)}")
                for line in self.rxBuffer:
                    try:
                        print(struct.unpack_from('f', line.encode()))
                    except Exception:
                        pass

            elif cmd.startswith('dd') or cmd.startswith('getsamples'):
                nDropped = max(0, int(self.nTotalRecords - self.nRecDL))
                self.rxTimeoutTimer.stop()
                self.SBEDownloadComplete.emit(self.deviceName, int(self.nRecDL), int(nDropped))

            # Reset connection state for next command queue execution
            self.lastCommand = ''
            self.CTS = True
            self.rxTimeoutTimer.stop()

        # HANDLE SPECIAL RESPONSES AND TIMEOUTS
        elif ('startnow' in val.lower()) or ('start now' in val.lower()):
            self.sbeIsAsleep = True
            self.extraSleepy = 0
            self.attempts = 0
            self.CTS = True
            self.rxTimeoutTimer.stop()
            self.justStarted = True

        elif '<!--Repeat command' in val:
            # Re-send confirmation command required by SBE39plus
            self.serMonitor.txData(self.deviceName, self.lastCommand + '\r')

        elif 'timeout' in val.lower():
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

        self.calibration = {}
        full_text = "\n".join(self.rxBuffer)

        # --- Native SBE 39plus XML Parsing ---
        if '<CalibrationData' in full_text:
            # Extract all XML tags matching <KEY>value</KEY>
            matches = re.findall(r'<([A-Za-z0-9_]+)>\s*([^<]+)\s*</\1>', full_text)
            for key, val in matches:
                try:
                    self.calibration[key] = float(val)
                except ValueError:
                    self.calibration[key] = val

            self.rxBuffer = []
            return

        # --- Fallback: Legacy Text Parsing ---
        for line in self.rxBuffer:
            if '=' in line:
                parts = line.split('=')
                key = parts[0].strip()
                val_str = parts[1].strip()
                try:
                    self.calibration[key] = float(val_str)
                except ValueError:
                    self.calibration[key] = val_str
            elif 'temperature' in line.lower() and ':' in line:
                self.calibration['temp cal date'] = line.split(':')[1].strip()

        self.rxBuffer = []


    def processStatus(self):
        """processStatus extracts the status information received from the "ds"
        command and inserts it into a dict.
        """

        # Reset status dict
        self.status = {}

        full_text = "\n".join(self.rxBuffer)

        # --- Native SBE 39plus XML Parsing Branch ---
        if '<StatusData' in full_text or '<HardwareData' in full_text:
            # Helper function to extract content from XML tags like <TagName>value</TagName>
            def get_tag(tag, text):
                match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.IGNORECASE)
                return match.group(1).strip() if match else None

            self.status['device'] = 'SBE39plus'
            self.status['serial number'] = get_tag('SerialNumber', full_text) or ''

            # Parse Time: Native XML uses <DateTime>YYYY-MM-DDTHH:MM:SS</DateTime>
            time_str = get_tag('DateTime', full_text)
            if time_str:
                try:
                    # Try ISO format first (2026-09-05T06:55:00)
                    self.status['time'] = datetime.datetime.strptime(time_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    try:
                        self.status['time'] = datetime.datetime.strptime(time_str, '%d %b %Y %H:%M:%S')
                    except ValueError:
                        self.status['time'] = time_str

            self.status['voltage'] = get_tag('MainState', full_text) or get_tag('Vmain', full_text) or ''
            self.status['sample interval'] = get_tag('SampleInterval', full_text) or '0'
            self.status['sample number'] = get_tag('Samples', full_text) or get_tag('SampleNumber', full_text) or '0'
            self.status['logging status'] = 'logging' if get_tag('LoggingState', full_text) == '1' else 'not logging'
            self.status['real-time output'] = 'yes' if get_tag('OutputRealTime', full_text) == '1' else 'no'

            self.rxBuffer = []
            return

        # --- Fallback: Legacy SBE 39 Text Parsing Branch ---
        for line in self.rxBuffer:
            if 'serial no' in line.lower():
                parts = line.split('  ')
                verChar = 'V' if 'V' in parts[0] else 'v'
                self.status['device'] = parts[0].split(verChar)[0].strip()
                self.status['version'] = parts[0].split(verChar)[1].strip()
                self.status['serial number'] = parts[1].split('.')[1].strip() if len(parts) > 1 else ''

                if len(parts) >= 3:
                    time_str = parts[2].strip() if verChar == 'v' else ' '.join(parts[3:5]).strip()
                    try:
                        self.status['time'] = datetime.datetime.strptime(time_str, '%d %b %Y %H:%M:%S')
                    except ValueError:
                        pass

            elif 'volt' in line.lower():
                if 'low battery' in line.lower():
                    self.lowBattery = True
                    continue
                volt_parts = line.split(',')
                self.status['voltage'] = volt_parts[0].split('=')[1].strip() if '=' in volt_parts[0] else ''

            elif 'logging' in line.lower():
                self.status['logging status'] = 'not logging' if 'not' in line.lower() else 'logging'

            elif 'interval' in line.lower() and '=' in line:
                self.status['sample interval'] = line.split('=')[1].strip()

            elif 'samplenumber' in line.lower() or 'sample number' in line.lower():
                if '=' in line:
                    line_parts = line.split(',')
                    self.status['sample number'] = line_parts[0].split('=')[1].strip()

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
        time_str = time.strftime("%Y%m%d%H%M%S")
        if start:
            return [f'StartDateTime={time_str}']
        return [f'DateTime={time_str}']


class SBEError(Exception):
    def __init__(self, msg, parent=None):
        self.errText = msg
        self.parent = parent

    def __str__(self):
        return repr(self.errText)
