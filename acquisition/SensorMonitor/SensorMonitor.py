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
.. module:: SensorMonitor

    :synopsis: SensorMonitor watches a collection of devices or sensors
               connected via serial or network ports ports and emits a
               signal when data is received from any of the devices.
               The data is optionally parsed. It allows you to easily
               send and receive data to/from your devices or sensors.

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assesment and Conservation Engineering Group (MACE)
|
| Author:
|       Rick Towler   <rick.towler@noaa.gov>
| Maintained by:
|       Rick Towler   <rick.towler@noaa.gov>
"""


from PyQt6.QtCore import pyqtSignal, QObject, QThread, pyqtSlot
from . import SerialDevice, UDPDevice


class SensorMonitor(QObject):
    """A class for acquiring data from multiple sensors that emit data via
    serial ports, TCP and UDP.

    SensorMonitor watches a collection of serial ports, TCP, and UDP ports and
    emits a signal when data is received by any of the monitored ports. It is
    primarily designed to handle ASCII like data where messages are terminated
    with LF, CR+LF, or CR. Message data is buffered until a complete line is
    received. The line can optionally be parsed and the resulting output is
    passed from the monitoring thread to SensorMonitor via Qt's signal/Slot
    mechanism which which re-emits these signals so they can be handled by the
    application's sensor data event handling method. SensorMonitor handles both
    sending and receiving of data and thus can be used for polled sensors and
    for general I/O. (UDP based sensors support receive only.)

    **Public Methods**

    **addDevice** -- add a device to the list of devices that
    SensorMonitor watches.

    **removeDevice** -- Remove a device from the list of devices that
    SensorMonitor watches. If the device is currently being monitored,
    the acquisition thread is stopped and the serial port is closed.

    **startMonitoring** -- Start monitoring all (or optionally some) of the
    devices that have been registered by calls to addDevice. Calling
    startMonitoring will open the serial ports and start the acquisition
    threads for the specified devices.

    **stopMonitoring** -- Stop monitoring all (or optionally some) of the
    devices that have been registered by calls to addDevice. The acquisition
    threads are stopped and the serial ports closed for the specified devices.

    **Signals**

    **SensorDataReceived** -- This signal is emitted when a complete line of
    data is received by one of the monitored serial ports. If the line is
    parsed, the signal is only emitted if the parsing method returns data.

    Applications wishing to receive data from SensorMonitor must connect
    this signal to a method that accepts the following parameters:

        @rtype: String
        @returns: The device name string, as defined in the call to addDevice.
        @rtype: String
        @returns: The data received by the port identified by the device name.
        @rtype: Exception
        @returns: If there is an error parsing the data, this will be a
                  SensorError object containing the error information.

    """

    #  define this class's signals
    SerialControlState = pyqtSignal(str, str, bool)
    SerialControlChanged = pyqtSignal(str, dict)
    SensorDataReceived = pyqtSignal(str, str, object)
    SensorsStopped = pyqtSignal()
    SensorError = pyqtSignal(str, object)
    txSensorData = pyqtSignal(str, str)
    getSerialCTL = pyqtSignal(str)
    setSerialRTS = pyqtSignal(str, bool)
    setSerialDTR = pyqtSignal(str, bool)
    stopDevice = pyqtSignal(list)


    def __init__(self, parent=None):
        """Initialize this SensorMonitor instance."""
        super(SensorMonitor, self).__init__(None)

        #  create the devices dictionary which is keyed by device name and stores the
        #  various parameters for that device.
        self.devices = dict()

        self.nThreads = 0


    def addDevice(self, deviceName, port, baud, parseType, parseExp, parseIndex, cmdPrompt='',
                  byteSize=8, parity='N', stopBits=1, flowControl='NONE', pollRate=500,
                  txRate=500, initialState = (True, True), udpTxOnly=False):
        """Add a device to the list of devices that SensorMonitor watches.

        *deviceName* is a string that serves as a unique identfier for the serial port.
        This name will be included in the emitted signals to associate data with a device.

        *port* is a string containing the platform specific serial port identifier. For
        example, on windows systems it would be ``'COM1'`` or ``'COM12'``. On Linux systems it
        would be ``'/dev/ttyS0'`` or similar. You can also specify the IP address and port
        for RFC 2217 Network ports by setting the port string to 'rfc2217://<host>:<port>'
        You can specify the IP address and port for a TCP based socket by setting the port
        string to 'socket://<host>:<port>' and a UDP based socket by setting the port
        string to 'udp://<host>:<port>'

        *baud* is the serial port baud rate such as 9600 or 115200 etc.

        *parseType* specifies how the incoming data is parsed before the data is emitted
        via the *SensorDataReceived* signal. Valid values are:

            ``None`` -- No parsing is performed but newline characters are stripped.

            ``Delimited`` -- The incoming line is parsed using a delimiter. The delimiter
            is specified in the *parseExp* argument and the *parseIndex* argument specifies
            which field is returned.

            ``RegEx`` -- The incoming line is parsed using a regular expression. The regex
            is passed via the *parseExp* argument and and the *parseIndex* argument specifies
            which field is returned.

            ``RFIDFDXB`` -- This is a fixed length parser that assumes the data conforms to
            the FDX-B RFID tag specification. The *parseIndex* argument specifies the length
            in bytes of the datagram which for now should be specified as 8.

            ``HexEncode`` -- This is a fixed length parser that assumes the data is hex encoded.
            The *parseIndex* argument specifies the length in bytes of the datagram.

            ``FixedLen`` -- This is a generic fixed length parser that simply returns data in
            chunks of bytes the size of which is specified in the *parseIndex* argument.

            ``RAMSES`` -- This is a specialized fixed length parser for the RAMSES-ACC series of
            hyperspectral radiometers. Set *parseExp* and *parseIndex* to NONE.

        *parseExp* is a string defining either the parsing delimiter if *parseType* is 1
        or the regular expression if *parseType* is set to 2. If `parseType` is 0, specify
        an empty string ``''``.

        *parseIndex* is a number that is the index into the list returned by the parsing
        method of the data element of interest. This parameter must be specified even if
        only 1 element is returned from the parsing method (in which case *parseIndex*
        would be set to ``0``. For the fixed length parsers this argument specified the length
        of the message that should be returned.

        *cmdPrompt* (optional) is a string that specifies the command prompt for instruments
        that require user interaction. Text based UI's that require user interaction may
        output a command prompt which lacks a newline character. Setting *cmdPrompt* to
        the text of this command prompt will result in the command prompt line being
        handled like a regular line where the text of the command prompt is emitted via
        the *SensorDataReceived* signal. This allows the method handling the
        *SensorDataReceived* signal to "respond" to the command prompt.

        *byteSize* (optional) a number specifying the number of data bits. Possible values
        are ``5``, ``6``, ``7``, and ``8``. Default is ``8``.

        *parity* (optional) a string specifying the serial port parity checking method.
        Possible values are ``N`` for None, ``E`` for Even, ``O`` for Odd, ``M`` for Mark,
        and ``S`` for Space. Default is ``N``.

        *stopBits* (optional) a number specifying the number of stop bits. Possible values
        are ``1``, ``1.5``, and ``2``. Default is ``1``.

        *flowControl* (optional) a string specifying the flow control method. Possible
        values are ``RTSCTS`` for RTS/CTS hardware flow control, ``DSRDTR`` for DSR/DTR
        hardware flow control, ``SOFTWARE`` for XON/XOFF software flow control and
        ``NONE`` for no flow control. Default is ``NONE``.

        *pollRate* (optional) a number specifying the rate (in Hz) that the serial port
        is polled. During polling the input buffer is checked for data and if data is present
        the buffer is read from. Valid values are in the range of 1-1000 Hz.
        The default value is 1000 Hz.

        *txRate* (optional) a number specifying the rate (in Hz) that the tx buffer
        is polled. During polling the output buffer is checked for data and if data is present
        one "line" of data is transmitted. This value can be set to help throttle transmits
        to devices that cannot keep up with the flow of data. Valid values are in the range
        of 1-1000 Hz. The default value is 1000 Hz.

        *initialState* (optional) a 2-tuple of booleans containing the initial state of the
        control lines RTS and DTR (in that order) for the serial port when added to the
        monitor

        *udpTxOnly* (optional) Set to True to suppres the creation of the receive port when
        creating a UDP port. This only applies to UDP ports and is only used when sending
        data to from same machine you are receiving on
        """

        if deviceName in self.devices:
            #  device name is already in use - issue error
            raise SensorError('Device name ' + deviceName + ' is already in use. Specify a unique name.')

        #  store the parameters for this device - we don't actually create the device here. We but
        #  create the SerialDevice or UDPDevice objecst when the device is started.
        self.devices[deviceName] = {'deviceName':deviceName,
                                    'port':port,
                                    'baud':baud,
                                    'parseType':parseType,
                                    'parseExp':parseExp,
                                    'parseIndex':parseIndex,
                                    'cmdPrompt':cmdPrompt,
                                    'byteSize':byteSize,
                                    'parity':parity,
                                    'stopBits':stopBits,
                                    'flowControl':flowControl,
                                    'pollRate':pollRate,
                                    'txRate':txRate,
                                    'initialState':initialState,
                                    'udpTxOnly':udpTxOnly,
                                    'remove': False,
                                    'thread':None}


    def startMonitoring(self, devices=None):
        """
          Start monitoring creates an instance of SensorMonitorThread for each device
          specified, moves the object to a new thread, and starts the thread. The
          SensorMonitorThread objects then open their serial port and start polling
          As data is received from the individual ports it is sent via the
          ``SensorDataReceived`` signal.

          You can start specific devices by setting the `devices` keyword to a list
          of device(s) you want to start. If you do not specify any devices, all
          devices will be started.
        """

        if devices == None:
            #  no devices specified - get a list of all devices
            devices = self.devices.keys()
        elif (type(devices) is str):
            #  device was specified as a string, put it in a list
            devices = [devices]

        #  iterate through the provided devices, starting each one
        for device in devices:

            #  check if this device is already running
            if self.devices[device]['thread']:
                #  it is, skip it
                continue

            #  parse the device port to determine if this is a UDP based port which
            #  is a special case not handled by pySerial. UDP ports are specified
            #  in a similar fashion as TCP ports, but instead of "socket", you specify
            #  "udp". For example: udp://0.0.0.0:1234
            doUDP = False
            portParts = self.devices[device]['port'].split(':')
            if len(portParts) > 1:
                #  this must be either a socket or udp based port
                if portParts[0].lower() == 'udp':
                    #  this is a udp based port
                    doUDP = True

            #  create the sensorDevice object
            if not doUDP:
                sensorDevice = SerialDevice.SerialDevice(self.devices[device])
            else:
                sensorDevice = UDPDevice.UDPDevice(self.devices[device])

            #  connect us to the SensorMonitorThread's signals
            sensorDevice.SensorDataReceived.connect(self.dataReceived)
            sensorDevice.SerialControlChanged.connect(self.controlDataChanged)
            sensorDevice.DCEControlState.connect(self.controlDataState)
            sensorDevice.SensorError.connect(self.error)

            #  connect our signals to the SensorMonitorThread
            self.txSensorData.connect(sensorDevice.write)
            self.getSerialCTL.connect(sensorDevice.getControlLines)
            self.setSerialRTS.connect(sensorDevice.setRTS)
            self.setSerialDTR.connect(sensorDevice.setDTR)
            self.stopDevice.connect(sensorDevice.stopPolling)

            #  create a thread to run the monitor in
            thread = QThread(self)

            #  move the monitor to it
            sensorDevice.moveToThread(thread)

            #  connect thread specific signals and slots - this facilitates starting,
            #  stopping, and deletion of the threads.
            thread.started.connect(sensorDevice.startPolling)
            sensorDevice.SensorClosed.connect(self.sensorStopped)
            thread.finished.connect(self.threadCleanup)
            thread.finished.connect(thread.deleteLater)

            #  store references to our new objects and keep count
            self.devices[device]['thread'] = thread
            self.devices[device]['object'] = sensorDevice
            self.nThreads += 1

            #  and finally, start the thread - this will also start polling
            thread.start()


    def stopMonitoring(self, devices=None):
        """
          StopMonitoring emits the ``stopDevice`` signal which informs the
          SerialDevice thread to stop polling, flush and close the serial port, and
          terminate the thread. The device name and settings will be maintained and
          you can call startMonitoring

          You can stop specific devices by setting the `devices` keyword to a list
          of device(s) you want to stop. If you do not specify any devices, all
          devices will be stopped.
        """

        #  first check if any devices are running
        if self.nThreads == 0:
            #  no devices are running so just emit the SensorsStopped signal
            self.SensorsStopped.emit()
        else:
            #  at least one device is being monitored so tell the device(s) to stop
            if devices == None:
                #  no devices specified - get a list of all devices
                devices = list(self.devices.keys())
            elif (type(devices) is str):
                #  device was specified as a string, put it in a list
                devices = [devices]

            #  emit the stopDevice signal to inform device threads to shut down
            self.stopDevice.emit(devices)


    def removeDevice(self, devices=None):
        """removeDevice stops a running device (if needed) and then removes it
        from SensorMonitor. You can specify the device to remove, but if you
        omit the argument, all devices are removed.

        """

        if devices == None:
            #  no devices specified - get a list of all devices
            devices = list(self.devices.keys())
        elif (type(devices) is str):
            #  device was specified as a string, put it in a list
            devices = [devices]

        #  first get a list of running devices
        runningDevices = self.whosMonitoring()

        #  check our list of devices to remove against the list of running devices.
        for device in devices:
            if device in runningDevices:
                #  this device is running - set it for removal and then tell it to stop
                self.devices[device]['remove'] = True
                self.stopDevice.emit([device])
            else:
                #  this device is already stopped - just remove it
                del self.devices[device]


    def whosMonitoring(self):
        """Returns a list of currently running serial devices"""
        runningDevices = []
        for device in self.devices:
            #  assume if thread is populated, then the thread is running
            if self.devices[device]['thread']:
                runningDevices.append(device)

        return runningDevices


    def setDTR(self, deviceName, state):
        """Set the DTR line on the specified serial port

        """
        if deviceName in self.devices:
            self.setSerialDTR.emit(deviceName, state)


    def setRTS(self, deviceName, state):
        """Set the RTS line on the specified serial port

        """
        if deviceName in self.devices:
            self.setSerialRTS.emit(deviceName, state)


    def txData(self, deviceName, data):
        """Transmit data to the specified device

        `deviceName` must be set to the name of a configured device
        """

        #  send the txSensorData signal to the monitoring threads
        if deviceName in self.devices:
            self.txSensorData.emit(deviceName, data)


    def getControlLines(self, deviceName):
        """
            Request the status of the DCE control lines. The data is returned as a
            list of booleans ordered as [CTS, DSR, RI, CD].
        """
        self.getSerialCTL.emit(deviceName)


    @pyqtSlot(str, str, object)
    def dataReceived(self, deviceName, data, err):
        # consolidates the RX data signals from the individual monitoring threads and re-emit
        self.SensorDataReceived.emit(deviceName, data, err)


    @pyqtSlot(str, list)
    def controlDataState(self, deviceName, state_list):
        # consolidates the signals from the individual monitoring threads and re-emit
        state = {'CTS':state_list[0],
                 'DSR':state_list[1],
                 'RI':state_list[2],
                 'CD':state_list[3]}
        self.SerialControlChanged.emit(deviceName, state)


    @pyqtSlot()
    def controlDataChanged(self, deviceName, line, state):
        # consolidates the signals from the individual monitoring threads and re-emit
        self.SerialControlState.emit(deviceName, state)


    @pyqtSlot(str, object)
    def error(self, deviceName, errorObj):
        # consolidates the error signals from the individual monitoring threads and re-emit
        self.SensorError.emit(deviceName, errorObj)


    @pyqtSlot(str)
    def sensorStopped(self, deviceName):
        """sensorStopped is called when a device's port is closed. After the port
        is closed, we stop the thread. Final thread cleanup is handled in
        threadCleanup()

        This method should not be called directly.
        """

        if self.devices[deviceName]['thread']:
            self.devices[deviceName]['thread'].quit()


    @pyqtSlot()
    def threadCleanup(self):
        """
          threadCleanup is called when a SensorMonitorThread thread instance finishes
          running and emits the "finished" signal. This method cleans up references
          to that thread and SensorMonitorThread object.

          This method should not be called directly.
        """

        #  get a reference to the thread that is shutting down
        thread = QObject.sender(self)

        #  look for this thread in our device dict. If we find it, we
        #  dereference the python references to our thread and sensor
        #  object. At this point we know they have been destroyed on
        #  the Qt side, so we can dereference them so they can be
        #  garbage collected without error.
        for device in self.devices:
            if thread == self.devices[device]['thread']:
                self.devices[device]['thread'] = None
                self.devices[device]['object'] = None
                self.nThreads -= 1

                #  check if we're removing this device
                if self.devices[device]['remove']:
                    del self.devices[device]

        if self.nThreads == 0:
            self.SensorsStopped.emit()


#
#  SensorMonitor Exception class
#
class SensorError(Exception):
    def __init__(self, msg, parent=None):
        self.errText = msg
        self.parent = parent

    def __str__(self):
        return repr(self.errText)
