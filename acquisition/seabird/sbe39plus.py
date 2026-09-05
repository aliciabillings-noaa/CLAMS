"""
sbe39plus is a class that provides an interface for interacting with the Sea-Bird SBE 39plus
bathythermograph using its native XML command interface.
"""

import datetime
import struct
import re
from PyQt6.QtCore import *
from acquisition.SensorMonitor import SensorMonitor


class sbe39plus(QObject):
    """A class for downloading data from and setting parameters on the Sea Bird SBE 39plus
    bathythermograph operating in native mode.
    """

    # Define the sbe39plus class's signals
    SBETimeout = pyqtSignal(str)
    SBEData = pyqtSignal(str, str)
    SBEConnected = pyqtSignal(str)
    SBEDownloadData = pyqtSignal(str, list)
    SBEProgress = pyqtSignal(str, float)
    SBEAbort = pyqtSignal(str)
    SBEStatus = pyqtSignal(str, dict)
    SBECalibration = pyqtSignal(str, dict)
    SBEDownloadComplete = pyqtSignal(str, int, int)

    def __init__(self, serialPort, deviceName='SBE39Plus', baud=9600, serialMonitor=None, parent=None):
        QObject.__init__(self, parent)

        # Internal state variables
        self.deviceName = deviceName
        self.rxBuffer = []
        self.txBuffer = []
        self.status = {}
        self.calibration = {}
        self.connected = False
        self.lowBattery = False
        self.sbeIsAsleep = False
        self.binaryUploadEnable = False
        self.isAborting = False
        self.justStarted = False
        self.nTotalRecords = 0
        self.CTS = True
        self.nRecDL = 0
        self.maxConAttempts = 200
        self.extraSleepy = 0
        self.lastCommand = ''

        # Use provided SerialMonitor or instantiate a new one
        if serialMonitor is None:
            self.serMonitor = SensorMonitor.SensorMonitor()
        else:
            self.serMonitor = serialMonitor

        self.serMonitor.SensorDataReceived.connect(self.rxData)

        # Register device with SensorMonitor using default prompt
        self.serMonitor.addDevice(deviceName, serialPort, baud, 'None', '', 0,
                                  cmdPrompt='S>', pollRate=1000)

        # Transmit timer
        self.txTimer = QTimer(self)
        self.txTimer.setSingleShot(False)
        self.txTimer.setInterval(100)
        self.txTimer.timeout.connect(self.pollTxBuffer)

        # Response timeout timer
        self.rxTimeoutTimer = QTimer(self)
        self.rxTimeoutTimer.setSingleShot(True)
        self.rxTimeoutTimer.setInterval(3000)
        self.rxTimeoutTimer.timeout.connect(self.rxTimeout)


    def setConnectionParams(self, serialPort, baud):
        """setConnectionParams updates the serial parameters when disconnected."""
        if not self.connected:
            self.serMonitor.removeDevice(self.deviceName)
            self.serMonitor.addDevice(self.deviceName, serialPort, baud, 'None', '', 0,
                                      cmdPrompt='S>', pollRate=1000)


    def connect(self):
        """Connects to the serial port and wakes up the SBE 39plus."""
        if not self.connected:
            try:
                self.serMonitor.startMonitoring(devices=[self.deviceName])
                self.connected = True
                self.isConnecting = True
                self.sbeIsAsleep = True
                self.attempts = 0

                # Queue initial wake command
                self.txCommand([''])
                self.txTimer.start()
            except Exception as e:
                raise e


    def getStatus(self):
        """Requests status using native SBE 39plus 'GetSD' command."""
        if self.connected:
            self.txCommand(['GetSD'])


    def setTxRealTime(self, state):
        """Enables or disables real-time output using native OutputRealTime= command."""
        if self.connected:
            state_str = 'Y' if state else 'N'
            self.txCommand([f'OutputRealTime={state_str}'])


    def setSamplingInterval(self, num):
        """Sets the sampling interval in seconds using SampleInterval= command."""
        if self.connected:
            num = int(num)
            num = max(0, min(num, 32767))
            self.txCommand([f'SampleInterval={num}'])


    def setBaud(self, baud):
        """Sets serial baud rate on the device."""
        if self.connected:
            validRates = [1200, 2400, 4800, 9600, 19200, 38400]
            if baud in validRates:
                self.txCommand([f'BAUD={baud}'])
            else:
                raise SBEError(f'Invalid baud rate: {baud}.')


    def setSampleNumber(self, num):
        """Resets the internal sample storage index."""
        if self.connected:
            self.stop()
            num_str = str(int(num))
            self.txCommand([f'SAMPLENUM={num_str}'])
            self.lastCommand = f'SAMPLENUM={num_str}'


    def sleep(self):
        """Puts device into low-power sleep mode."""
        if self.connected:
            self.txCommand(['QS'])


    def getCalParms(self):
        """Requests calibration coefficients using native GetCC command."""
        if self.connected:
            self.txCommand(['GetCC'])


    def disconnect(self):
        """Closes serial connection and resets state."""
        if self.connected:
            self.serMonitor.stopMonitoring(devices=[self.deviceName])
            self.txTimer.stop()
            self.rxTimeoutTimer.stop()

            self.connected = False
            self.calibration = {}
            self.status = {}
            self.rxBuffer = []
            self.txBuffer = []


    def stop(self):
        """Stops active logging session."""
        if self.connected:
            self.txCommand(['STOP'])


    def startNow(self):
        """Starts logging immediately."""
        if self.connected:
            self.txCommand(['STARTNOW'])


    def startLater(self):
        """Starts logging at configured start date/time."""
        if self.connected:
            self.txCommand(['STARTLATER'])


    def setStartDateTime(self, time=None, delay=None, localTime=False):
        """Sets delayed start date/time in native YYYYMMDDHHMMSS format."""
        if self.connected:
            if time is None:
                if localTime:
                    time = datetime.datetime.now()
                else:
                    time = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            if delay:
                time = time + datetime.timedelta(minutes=delay)

            self.txCommand(self.formatTime(time, start=True))


    def download(self, start=1, stop=None, mode='ASCII'):
        """Downloads samples using native GetSamples:start,stop command."""
        if self.connected:
            if stop:
                stop = int(stop)
            else:
                stop = int(self.status.get('sample number', 0))
                if stop > 5:
                    stop = stop - 4

            self.dlProgress = 0
            self.nRecDL = 0
            self.nTotalRecords = max((stop - int(start)) + 1, 1)

            start_str = str(int(start))
            stop_str = str(int(stop))

            self.txCommand([f'GetSamples:{start_str},{stop_str}'])


    def abort(self):
        """Sends control+C interrupt signal."""
        self.isAborting = True
        self.serMonitor.txData(self.deviceName, '\x03\r')


    def setRTC(self, time=None, localTime=False):
        """Sets internal real-time clock."""
        if self.connected:
            self.stop()
            if time is None:
                if localTime:
                    time = datetime.datetime.now()
                else:
                    time = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

            self.txCommand(self.formatTime(time))


    def txCommand(self, cmdList):
        """Enqueues command list to transmit buffer."""
        for cmd in cmdList:
            self.txBuffer.append(cmd + '\r')


    def pollTxBuffer(self):
        """Processes transmit queue and wake-up attempts."""
        if self.connected and len(self.txBuffer) > 0:
            if self.sbeIsAsleep:
                if self.attempts < self.maxConAttempts:
                    # Send GetSD to wake SBE 39plus cleanly
                    self.serMonitor.txData(self.deviceName, 'GetSD\r')
                    self.attempts += 1
                else:
                    self.disconnect()
                    self.SBETimeout.emit(self.deviceName)
            else:
                if self.CTS:
                    cmd = self.txBuffer.pop(0)
                    self.serMonitor.txData(self.deviceName, cmd)
                    self.lastCommand = cmd

                    if cmd == 'QS':
                        self.sbeIsAsleep = True
                        self.extraSleepy = 0
                        self.attempts = 0

                    self.CTS = False
                    self.rxTimeoutTimer.start()


    def rxData(self, name, val, err):
        """Processes incoming data buffer from SensorMonitor."""
        if ('stop' in self.lastCommand.lower()) and ('inactive command' in val.lower()):
            return

        if val:
            self.SBEData.emit(self.deviceName, val)

        if (val == 'S>') and self.justStarted:
            self.justStarted = False
            val = ''

        # Wake up check accepting S> or SBE 39plus XML tags
        if self.sbeIsAsleep and (val == 'S>' or '<ExecCommand' in val or '<Executed' in val or val.strip() == '<Executed/>'):
            self.sbeIsAsleep = False
            self.extraSleepy = 0
            if self.isConnecting:
                self.SBEConnected.emit(self.deviceName)
                self.isConnecting = False

        if '<datapacket>' in val.lower():
            return

        if not self.CTS:
            self.rxTimeoutTimer.start()

        cmd = self.lastCommand.lower().strip()

        # Buffer response XML metadata
        if (cmd.startswith('getsd') or cmd.startswith('gethd') or cmd.startswith('getcc') or
                cmd.startswith('ds') or cmd.startswith('dc')):
            self.rxBuffer.append(val)

        # Parse sample download streams
        elif cmd.startswith('getsamples') or cmd.startswith('dd'):
            if val != 'S>' and not val.startswith('</'):
                clean_val = re.sub(r'<[^>]+>', '', val).strip()
                if clean_val:
                    parts = [p.strip() for p in clean_val.split(',')]
                    if len(parts) >= 3:
                        try:
                            temp = float(parts[0])
                            if len(parts) == 4:
                                pressure = float(parts[1])
                                time_str = f"{parts[2]} {parts[3]}"
                            else:
                                pressure = 0.0
                                time_str = parts[1] if len(parts) == 2 else f"{parts[1]} {parts[2]}"

                            try:
                                time = datetime.datetime.strptime(time_str, '%d %b %Y %H:%M:%S')
                            except ValueError:
                                time = datetime.datetime.strptime(time_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')

                            self.nRecDL += 1.0
                            self.SBEDownloadData.emit(self.deviceName, [time, temp, pressure])

                            if self.nTotalRecords > 0:
                                dlProgress = (self.nRecDL / self.nTotalRecords) * 100.0
                                if dlProgress != self.dlProgress:
                                    self.dlProgress = dlProgress
                                    self.SBEProgress.emit(self.deviceName, self.dlProgress)

                        except Exception:
                            pass

        # Detect command execution end
        if val == 'S>' or '</StatusData>' in val or '</CalibrationData>' in val or '</HardwareData>' in val or '<Executed/>' in val:
            if self.isAborting:
                self.isAborting = False
                self.SBEAbort.emit(self.deviceName)

            elif cmd.startswith('getsd') or cmd.startswith('gethd') or cmd.startswith('ds'):
                self.processStatus()
                self.SBEStatus.emit(self.deviceName, self.status)

            elif cmd.startswith('getcc') or cmd.startswith('dc'):
                self.processCalParms()
                self.SBECalibration.emit(self.deviceName, self.calibration)

            elif cmd.startswith('getsamples') or cmd.startswith('dd'):
                nDropped = max(0, int(self.nTotalRecords - self.nRecDL))
                self.rxTimeoutTimer.stop()
                self.SBEDownloadComplete.emit(self.deviceName, int(self.nRecDL), int(nDropped))

            self.lastCommand = ''
            self.CTS = True
            self.rxTimeoutTimer.stop()

        elif ('startnow' in val.lower()) or ('start now' in val.lower()):
            self.sbeIsAsleep = True
            self.extraSleepy = 0
            self.attempts = 0
            self.CTS = True
            self.rxTimeoutTimer.stop()
            self.justStarted = True

        elif '<!--Repeat command' in val:
            self.serMonitor.txData(self.deviceName, self.lastCommand + '\r')

        elif 'timeout' in val.lower():
            self.sbeIsAsleep = True
            self.attempts = 0


    def processCalParms(self):
        """Parses calibration values from GetCC XML or text response."""
        self.calibration = {}
        full_text = "\n".join(self.rxBuffer)

        if '<CalibrationData' in full_text:
            matches = re.findall(r'<([A-Za-z0-9_]+)>\s*([^<]+)\s*</\1>', full_text)
            for key, val in matches:
                try:
                    self.calibration[key] = float(val)
                except ValueError:
                    self.calibration[key] = val
            self.rxBuffer = []
            return

        for line in self.rxBuffer:
            if '=' in line:
                parts = line.split('=')
                key = parts[0].strip()
                val_str = parts[1].strip()
                try:
                    self.calibration[key] = float(val_str)
                except ValueError:
                    self.calibration[key] = val_str

        self.rxBuffer = []


    def processStatus(self):
        """Parses status attributes from GetSD XML or text response."""
        self.status = {}
        full_text = "\n".join(self.rxBuffer)

        if '<StatusData' in full_text or '<HardwareData' in full_text:
            def get_tag(tag, text):
                match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.IGNORECASE)
                return match.group(1).strip() if match else None

            self.status['device'] = 'SBE39plus'
            self.status['serial number'] = get_tag('SerialNumber', full_text) or ''

            time_str = get_tag('DateTime', full_text)
            if time_str:
                try:
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

        self.rxBuffer = []


    def rxTimeout(self):
        """Handles connection response timeout."""
        self.disconnect()
        self.SBETimeout.emit(self.deviceName)


    def __del__(self):
        if self.connected:
            self.serMonitor.stopMonitoring(devices=[self.deviceName])


    def formatTime(self, time, start=False):
        """Formats datetime to YYYYMMDDHHMMSS."""
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