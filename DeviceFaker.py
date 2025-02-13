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
.. module:: DeviceFaker

    :synopsis: DeviceFaker can be used to send simulated device data
               to CLAMS. It simulates 4 devices: specimen scale,
               basket scale, length board and barcode reader and can
               be used for testing CLAMS reception and processing
               of device data without actually having devices connected
               to your workstation.

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
"""


import sys
import string
import yaml
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from acquisition.SensorMonitor import SensorMonitor
from ui import ui_DeviceFaker


class DeviceFaker(QMainWindow, ui_DeviceFaker.Ui_DeviceFaker):

    def __init__(self, config_file):
        super(DeviceFaker, self).__init__()
        self.setupUi(self)

        self.config_file = config_file
        self.logText = []
        self.maxDisplayLines = 200
        self.sensorsOpened = False

        #  restore the application state
        self.appSettings = QSettings('CLAMS', 'DeviceFaker')
        size = self.appSettings.value('winsize', QSize(476,300))
        position =  self.appSettings.value('winposition', QPoint(10,10))
        #  check the current position and size to make sure the app is on the screen
        position, size = self.checkWindowLocation(position, size)

        #  now move and resize the window
        self.move(position)
        self.resize(size)

        #  create a dict to hold our sensor "stuff". The top level keys
        #  must match the sensors defined in the config file
        self.sensors = {}

        #  store the various sensor
        self.sensors['specimen_scale'] = {'group':self.gbSpecimen,
                                          'text':self.sensorValue_Specimen,
                                          'button':self.pbSendValue_Specimen}
        self.sensors['basket_scale'] = {'group':self.gbBasket,
                                        'text':self.sensorValue_Basket,
                                        'button':self.pbSendValue_Basket}
        self.sensors['lengthboard'] = {'group':self.gbLengthboard,
                                       'text':self.sensorValue_Lengthboard,
                                       'button':self.pbSendValue_Lengthboard}
        self.sensors['barcode'] = {'group':self.gbBarcode,
                                   'text':self.sensorValue_Barcode,
                                   'button':self.pbSendValue_Barcode}

        #  create an instance of SensorMonitor to handle sensor IO
        self.sensorMonitor = SensorMonitor.SensorMonitor()

        #  connect signals for SensorMonitor
        self.sensorMonitor.SensorsStopped.connect(self.devicesClosed)
        self.sensorMonitor.SensorError.connect(self.sensorError)
        self.sensorMonitor.SensorDataReceived.connect(self.SensorDataReceived)

        #  connect the UI signals
        self.pbSendValue_Basket.clicked.connect(self.sendData)
        self.pbSendValue_Lengthboard.clicked.connect(self.sendData)
        self.pbSendValue_Specimen.clicked.connect(self.sendData)
        self.pbSendValue_Barcode.clicked.connect(self.sendData)

        #  complete startup in the applicationInit method
        timer =  QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(self.applicationInit)
        timer.start(0)


    def applicationInit(self):

        #  read the configuration file
        with open(self.config_file, 'r') as cf_file:
            try:
                self.configuration = yaml.safe_load(cf_file)
            except yaml.YAMLError as exc:
                errorMsg = ('Error reading configuration file ' + self.config_file +
                        ' ::: ' + str(exc))
                QMessageBox.critical(self, "Configuration Error", errorMsg)
                self.close()
                return

        if 'sensors' not in self.configuration:
            errorMsg = ('Error reading configuration file ' + self.config_file +
                        ' ::: ' + "Missing 'sensors' section.")
            QMessageBox.critical(self, "Configuration Error", errorMsg)
            self.close()
            return

        #  loop thru the sensors, setting them up
        for sensor_name in self.configuration['sensors']:
            if sensor_name in self.sensors:
                config = self.configuration['sensors'][sensor_name]
                sensor = self.sensors[sensor_name]
                if config['type'].lower() == 'udp':
                    port = 'udp://' + config['ip'] + ':' + str(config['port'])
                    baud = 0
                elif config['type'].lower() == 'tcp':
                    port = 'socket://' + config['ip'] + ':' + str(config['port'])
                    baud = 0
                elif config['type'].lower() == 'serial':
                    port = config['comport']
                    baud = config['baud']
                else:
                    errorMsg = ("Unknown sensor type '" + config['type'] + "' for " +
                            "sensor '" + sensor_name + "'. This sensor will be disabled.")
                    QMessageBox.warning(self, "Configuration Error", errorMsg)
                    continue

                #  add default pre and post data strings if they are missing
                if 'pre' not in config:
                    config['pre'] = ''
                if 'post' not in config:
                    config['post'] = ''
                sensor['pre'] = config['pre']
                sensor['post'] = config['post']

                #  add the device to SensorMonitor

                #  first, display a message about opening the sensor
                if config['type'].lower() in ['udp','tcp']:
                    infoText = "Opening network sensor: " + port
                else:
                    infoText = ("Opening serial sensor port: " + port +
                            "  Baud: " + str(baud))
                self.showText(sensor_name, infoText, color='blue')

                #  add the device based on the type - we have to handle UDP special
                if config['type'].lower() in ['serial','tcp']:
                    self.sensorMonitor.addDevice(sensor_name, port, baud, 'None', '', 0)
                else:
                    #  set the udpTxOnly property since we probably will be transmitting
                    #  to the same machine we're receiving on and we want CLAMS to
                    #  have access to the receive port.
                    self.sensorMonitor.addDevice(sensor_name, port, baud, 'None', '', 0,
                            udpTxOnly=True)

                #  enable this sensor's group box in the UI to indicate the
                #  sensor is working.
                sensor['group'].setEnabled(True)

        #  set the sensorsOpened prop to track when they are all closed.
        self.sensorsOpened = True

        #  now that all devices are added - start monitoring them. This will cause
        #  SensorMonitor to open serial or network ports and in the case of serial
        #  ports start polling.
        self.sensorMonitor.startMonitoring()

        #  If there are any errors opening ports, SensorMonitor will emit the
        #  SensorError signal for each device with an issue


    @pyqtSlot()
    def sendData(self):

        button = self.sender()
        for sensor in self.sensors:
            if button == self.sensors[sensor]['button']:
                text = (self.sensors[sensor]['pre'] + ' ' +
                        self.sensors[sensor]['text'].text() + ' ' +
                        self.sensors[sensor]['post'])
                text = text.strip()
                self.sensorMonitor.txData(sensor, text  + '\n')
                self.showText(sensor, " tx ::: " + text)


    @pyqtSlot(str, object)
    def sensorError(self, deviceName, obj):

        #  There was an issue with a device display a warning dialog
        warningText = obj.errText + " This device will be not be enabled."
        QMessageBox.warning(self, "Sensor/Device Error", warningText)
        self.showText(deviceName, warningText, color='red')

        #  disable this sensor in the UI
        if deviceName in self.sensors:
            self.sensors[deviceName]['group'].setEnabled(False)


    @pyqtSlot(str, str, object)
    def SensorDataReceived(self, deviceName, data, err):
        self.showText(deviceName, data)
        if err:
            self.showText(deviceName, str(err), color='red')


    @pyqtSlot()
    def devicesClosed(self):
        '''devicesClosed is called when the SensorMonitor emits the
        SensorsStopped signal which lets us know all acquisition
        threads have stopped. Once they are stopped we can close the
        form without error. (Qt gets angry when threads are destroyed
        while running.) Set sensorsOpened to True and call close()
        again.
        '''

        #  set sensorsOpened to False and call close() again
        self.sensorsOpened = False
        self.showText('', 'All devices closed. Exiting...', color='blue')
        self.close()


    def showText(self, name, val, color='black'):
        '''
        showText formats the text for display in the GUI
        '''

        if val:
            #  filter any non-printable characters
            val = ''.join(filter(lambda x:x in string.printable, val))

            #  update the display with this new line of text
            text = '<text style="color:' + color + '">' + name + ' ::: ' + val + '<br/>'
            self.logText.append(text)
            if len(self.logText) > self.maxDisplayLines:
                self.logText.pop(0)
            text = ''.join(self.logText)
            text = '<html><body><p>' + text + '</p></body></html>'
            self.textBrowser.setHtml(text)

            #  ensure that the window is scrolled to see the new line of text.
            scrollMax = self.textBrowser.verticalScrollBar().maximum()
            self.textBrowser.verticalScrollBar().setValue(scrollMax)


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


    def closeEvent(self, event):

        #  only exit when all sensors have closed
        if not self.sensorsOpened:
            #  all sensors closed. store the application size and position
            self.appSettings.setValue('winposition', self.pos())
            self.appSettings.setValue('winsize', self.size())

            #  and accept to close
            event.accept()
        else:
            #  tell SensorMonitor to shut down. SensorMonitor will signal after
            #  all threads have stopped.
            self.showText('', 'Shutting down sensors...', color='blue')
            self.sensorMonitor.stopMonitoring()

            #  lastly ignore this event for now and wait for
            #  our sensors to close
            event.ignore()


if __name__ == "__main__":

    import argparse

    #  define the default config file - a config file is required
    config_file = './DeviceFaker.yml'

    #  parse the command line arguments
    parser = argparse.ArgumentParser(description='DeviceFaker sends simulated device data to CLAMS')
    parser.add_argument("-f", "--config_file", help="Specify the path to the yml configuration file.")

    args = parser.parse_args()

    if (args.config_file):
        config_file = os.path.normpath(str(args.config_file))

    app = QApplication(sys.argv)
    form = DeviceFaker(config_file)
    form.show()
    app.exec()

