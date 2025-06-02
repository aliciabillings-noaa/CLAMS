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
.. module:: UDPDevice

    :synopsis: The UDPDevice class handles I/O for a UDP based sensor.
               It is simple class with an interface that mimics
               SerialDevice and is used by SensorMonitor when the user
               specifies a UDP based port.

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

import re
from PyQt6.QtCore import pyqtSignal, QObject, pyqtSlot
from PyQt6 import QtNetwork


class UDPDevice(QObject):

    """
    The UDPDevice class handles I/O for a UDP based sensor. It is simple class with
    an interface that mimics SerialDevice and is used by SensorMonitor when the user
    specifies a UDP based port:

        udp://0.0.0.0:1234

    and emits "whole messages" via the SensorDataReceived signal. Typically this class
    is used internally by the SensorMonitor class which manages the thread and the
    creation and destruction of this object.

    NOTE! This class does not support transmitting data.
    """

    #  define the UDPDevice class's signals
    DCEControlState = pyqtSignal(str, list)
    SerialControlChanged = pyqtSignal(str, str, bool)
    SensorDataReceived = pyqtSignal(str, str, object)
    SensorClosed = pyqtSignal(str)
    SensorError = pyqtSignal(str, object)

    def __init__(self, deviceParams):

        super(UDPDevice, self).__init__(None)

        #  set default values
        self.rxBuffer = ''
        self.txBuffer = []
        self.filtRx = ''
        self.rts = deviceParams['initialState'][0]
        self.dtr = deviceParams['initialState'][1]
        self.udp_socket = None
        self.tx_socket = None

        #  define a list that stores the state of the control lines: order is [CTS, DSR, RI, CD]
        self.controlLines = [False, False, False, False]

        #  define the maximum line length allowed - no sane input should exceed this
        self.maxLineLen = 16384

        #  set the device name
        self.deviceName = deviceParams['deviceName']

        #  set the parsing parameters
        if (deviceParams['parseType']):
            if deviceParams['parseType'].upper() == 'REGEX':
                self.parseType = 2
                try:
                    #  compile the regular expression
                    self.parseExp = re.compile(deviceParams['parseExp'])
                except Exception as e:
                    self.SensorError.emit(self.deviceName, SensorError('Invalid regular expression configured for ' +
                            self.deviceName, parent=e))
            elif deviceParams['parseType'].upper() == 'DELIMITED':
                self.parseType = 1
                self.parseExp = deviceParams['parseExp']
            elif deviceParams['parseType'].upper() == 'RFIDFDXB':
                self.parseType = 13
                self.parseExp = ''
                self.maxLineLen = int(deviceParams['parseIndex'])
            elif deviceParams['parseType'].upper() == 'HEXENCODE':
                self.parseType = 12
                self.parseExp = ''
                self.maxLineLen = int(deviceParams['parseIndex'])
            elif deviceParams['parseType'].upper() == 'FIXEDLEN':
                self.parseType = 11
                self.parseExp = ''
                self.maxLineLen = int(deviceParams['parseIndex'])
            else:
                self.parseType = 0
                self.parseExp = ''
        else:
            self.parseType = 0
            self.parseExp = ''

        try:
            self.parseIndex = int(deviceParams['parseIndex'])
        except:
            self.parseIndex = 0

        #  Set the command prompt  - This is required for devices that present a
        #  command prompt that must be responded to.
        self.cmdPrompt = deviceParams['cmdPrompt']
        self.cmdPromptLen = len(self.cmdPrompt)

        #  set the txOnly argument. This is a special parameter for the UDP
        #  socket that prohibits the creation of the receive socket and is
        #  used in cases where you are sending data to the same host you're
        #  receiving on. This is a very uncommon situation.
        self.txOnly = deviceParams['udpTxOnly']

#        try:
        #  create the local UDP port we'll use to listen on
        portParts = deviceParams['port'].split(':')
        self.ip = QtNetwork.QHostAddress(portParts[1].strip('/'))
        self.port = int(portParts[2])

#        except Exception as e:
#            self.SensorError.emit(self.deviceName, SensorError('Unable to create UDP based port for ' +
#                    self.deviceName + '. Invalid port option.', parent=e))
#            self.udp_socket = None


    @pyqtSlot()
    def startPolling(self):
        """
          Open the UDP port
        """

        #  check that we're not currently bound
        if self.udp_socket is None:
            try:
                #  create and open the UDP port
                if not self.txOnly:
                    self.udp_socket = QtNetwork.QUdpSocket(self)
                    self.udp_socket.readyRead.connect(self.udp_data_available)
                    self.udp_socket.bind(self.port)
                else:
                    self.udp_socket = None
                self.tx_socket = QtNetwork.QUdpSocket(self)
                self.tx_socket.bind()

            except Exception as e:
                self.SensorError.emit(self.deviceName, SensorError('Unable to open UDP based port for device ' +
                       self.deviceName + '.', parent=e))


    @pyqtSlot(list)
    def stopPolling(self, deviceList):
        """
          Close our UDP port and emit the SensorClosed signal
        """

        #  check if this signal is for us
        if (self.deviceName not in deviceList):
            #  this is not the droid we're looking for
            return

        #  disconnect readyRead and close the rx socket
        if self.udp_socket:
            try:
                self.udp_socket.readyRead.disconnect()
            except:
                pass
            if self.udp_socket.state().value > 0:
                #  close the receive socket
                self.udp_socket.close()

        #  close the Tx socket
        if self.tx_socket:
            if self.tx_socket.state().value > 0:
                self.tx_socket.close()

        #  emit the closed signal
        self.SensorClosed.emit(self.deviceName)


    @pyqtSlot(str, bool)
    def setRTS(self, deviceName, state):
        """
          Set/Unset the RTS line on this serial port. This method is not supported for
          UDP sockets
        """
        pass


    @pyqtSlot(str, bool)
    def setDTR(self, deviceName, state):
        """
          Set/Unset the DTR line on this serial port. This method is not supported for
          UDP sockets
        """
        pass


    @pyqtSlot(str)
    def getControlLines(self, deviceName):
        """
            Returns the state of the DCE control lines. This method is not supported for
            UDP sockets
        """
        if deviceName == self.deviceName:
            self.DCEControlState.emit(self.deviceName, self.controlLines)


    @pyqtSlot(str, str)
    def write(self, deviceName, data):
        """
          Write data to the UDP port.
        """
        if deviceName == self.deviceName:
            bytes = self.tx_socket.writeDatagram(data.encode(), self.ip, self.port)
            if bytes < 0:
                err = SensorError('Error writing datagram for ' + deviceName +
                        ': ' + self.udp_socket.errorString())
                self.SensorError.emit(deviceName, err)


    @pyqtSlot()
    def udp_data_available(self):

        #  get a reference to the port object that Rx'd the data
        udp_source = self.sender()

        while udp_source.hasPendingDatagrams():

            #  get the length of the next datagram and read it
            datagram_len = udp_source.pendingDatagramSize()
            data, source_host, source_port = udp_source.readDatagram(datagram_len)

            #  decode
            try:
                rxData = data.decode('utf-8')
            except:
                rxData = ''

            #  check if there is data in the buffer and append if so
            buffLength = len(self.rxBuffer)
            if buffLength > 0:
                rxData = self.rxBuffer + rxData
                #  reset the buffer
                self.rxBuffer = ''

            #  get the new length of our rx buffer
            buffLength = len(rxData)

            #  Parse the received data
            if (self.parseType <= 10):
                #  Parse types 0-10 are "line based" and are strings of chars
                #  that are terminated by an EOL (\n or \r\n) characters.

                #  check if we have to force the buffer to be processed
                if buffLength > self.maxLineLen:
                    #  the buffer is too big - force process it
                    rxData = rxData + '\n'

                #  split lines into a list
                lines = rxData.splitlines(True)

                #  loop thru the extracted lines
                for line in lines:
                    err = None
                    #  check for complete lines
                    if line.endswith('\n') or line.endswith('\r'):
                        #  this line is complete - strip the newline character(s) and whitespace
                        line = line.rstrip('\r\n').strip()

                        #  and make sure we have some text
                        if line:
                            #  we do, process line
                            try:
                                if self.parseType == 2:
                                    #  use regular expression to parse
                                    parts = self.parseExp.findall(line)
                                    data = parts[self.parseIndex]
                                elif self.parseType == 1:
                                    #  use a delimiter to parse
                                    parts = line.split(self.parseExp)
                                    data = parts[self.parseIndex]
                                else:
                                    # do not parse - pass whole line
                                    data = line
                            except Exception as e:
                                data = None
                                err = SensorError('Error parsing input from ' + self.deviceName + \
                                        '. Incorrect parsing configuration or malformed data stream.', \
                                        parent=e)

                            # emit a signal containing data from this line
                            self.SensorDataReceived.emit(self.deviceName, data, err)

                    elif (self.cmdPromptLen > 0) and (line[-self.cmdPromptLen:] == self.cmdPrompt):
                        #  this line (or the end of it) matches the command prompt
                        self.SensorDataReceived.emit(self.deviceName, line, err)

                    else:
                        #  this line of data is not complete - insert in buffer
                        self.rxBuffer = line

            elif (self.parseType <= 20):
                #  Parse types 11-20 are length based. This method of parsing acts on a
                #  fixed number of characters.

                #  loop thru the rx buffer extracting our fixed length chunks of data
                lines = []
                for i in range(0, (buffLength // self.maxLineLen)):
                    #  generate the start and end indices into our chunk
                    si = i * self.maxLineLen
                    ei = si + self.maxLineLen
                    #  extract it
                    lines.append(rxData[si:ei])
                    #  remove the chunk from the working rx buffer
                    rxData = rxData[ei:]

                #  place any partial chunks back in the buffer
                self.rxBuffer = self.rxBuffer + rxData

                #  loop thru the extracted chunks and process
                for line in lines:
                    err = None
                    #  process chunk
                    try:

                        if (self.parseType == 12):
                            #  encode the entire chunk as hex
                            data = line.encode('hex')

                        if (self.parseType == 13):
                            #  Process this as a type FDX-B RFID tag

                            #  this parsing is based on a single RFID reader which outputs a fixed 8 byte
                            #  datagram with no newline. It doesn't appear to support the "extra data block"
                            #  so that data is not handled by this parsing routine.

                            bstr = ''
                            for c in line:
                                #  construct the original binary stream
                                bstr = bin(ord(c))[2:].zfill(8) + bstr
                            #  decode the binary string into the ID code, Country code, data block status bit, and animal bit
                            data = [str(int(bstr[26:64],2)), str(int(bstr[16:26],2)), bstr[15], bstr[0]]

                        else:
                            # do not do anything - pass whole chunk
                            data = line

                    except Exception as e:
                        data = None
                        err = SensorError('Error parsing input from ' + self.deviceName + \
                                '. Incorrect parsing configuration or malformed data stream.', \
                                parent=e)

                    # emit a signal containing data from this line
                    self.SensorDataReceived.emit(self.deviceName, data, err)


#
#  UDPDevice Exception class
#
class SensorError(Exception):
    def __init__(self, msg, parent=None):
        self.errText = msg
        self.parent = parent

    def __str__(self):
        return repr(self.errText)
