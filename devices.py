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
.. module:: devices

    :synopsis: devices contains common code for setting up devices
               in CLAMS. Devices provide data to CLAMS like a GPS,
               scale, barcode reader or networked based sources
               like SCS or serial to Ethernet devices.



| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
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


def getSoftwareDevices(db, workstationID):
    '''getSoftwareDevices returns a dictionary, keyed by device name
    containing the device ID and device interface for software
    based devices connected to the specified workstation.

    Software devices are dialogs that capture a measurement value.
    '''
    devices = {}

    #  query the devices attached to this station
    sql = ("SELECT measurement_setup.device_id,devices.device_name," +
            "measurement_setup.measurement_type,measurement_setup.device_interface " +
            "FROM measurement_setup INNER JOIN DEVICES ON " +
            "measurement_setup.device_id=devices.device_id WHERE " +
            "measurement_setup.workstation_id=" +  workstationID +
            " AND devices.active=1 AND LOWER(measurement_setup.device_interface) IN " +
            "('software') GROUP BY measurement_setup.device_id," +
            "devices.device_name,measurement_setup.measurement_type," +
            "measurement_setup.device_interface")
    devQuery = db.dbQuery(sql)
    for deviceID, deviceName, measurementType, deviceInterface in devQuery:
        if deviceName not in devices:
            devices[deviceName] = {'id':deviceID, 'interface':deviceInterface.lower(),
                    'measurementTypes':[measurementType]}
        else:
            devices[deviceName]['measurementTypes'].append(measurementType)

    return devices


def getDevices(db, workstationID):
    '''getDevices returns a dictionary, keyed by device name
    containing the device ID and device interface for serial or network
    based devices connected to the specified workstation.
    '''

    devices = {}

    #  query the devices attached to this station
    sql = ("SELECT measurement_setup.device_id,devices.device_name," +
            "measurement_setup.measurement_type,measurement_setup.device_interface " +
            "FROM measurement_setup INNER JOIN DEVICES ON " +
            "measurement_setup.device_id=devices.device_id WHERE " +
            "measurement_setup.workstation_id=" +  workstationID +
            " AND devices.active=1 AND LOWER(measurement_setup.device_interface) IN " +
            "('scs','network','serial') GROUP BY measurement_setup.device_id," +
            "devices.device_name,measurement_setup.measurement_type," +
            "measurement_setup.device_interface")
    devQuery = db.dbQuery(sql)
    for deviceID, deviceName, measurementType, deviceInterface in devQuery:
        if deviceName not in devices:
            devices[deviceName] = {'id':deviceID, 'interface':deviceInterface.lower(),
                    'measurementTypes':[measurementType]}
        else:
            devices[deviceName]['measurementTypes'].append(measurementType)

    return devices


def getDeviceParameters(db, deviceName, deviceID, deviceInterface):

    #  query the connection parameters for this device
    sql = ("SELECT device_parameter,parameter_value FROM device_configuration" +
            " WHERE device_id=" + deviceID)
    paramQuery = db.dbQuery(sql)

    #  loop thru the parameters and stick in a dictionary
    connectionParams = {}
    for devParam, paramVal in paramQuery:
        connectionParams.update({devParam.lower():paramVal})

    #  extract the required parameters based on the device interface
    deviceInterface = deviceInterface.lower()
    if deviceInterface in ['network','scs']:
        #  This is a network based device
        if 'networkport' not in connectionParams:
            raise ValueError("The required 'NetworkPort' device_configuration " +
                    "parameter is missing for the network based device '" + deviceName + "'")
        port = connectionParams['networkport']
        baud = None

    elif deviceInterface == 'serial':
        #  this is a serial based - serialport and baudrate params are required
        if 'serialport' not in connectionParams:
            raise ValueError("The required 'SerialPort' device_configuration " +
                    "parameter is missing for serial device '" + deviceName + "'")
        port = connectionParams['serialport']

        if 'baudrate' not in connectionParams:
            raise ValueError("The required 'BaudRate' device_configuration " +
                    "parameter is missing for serial device '" + deviceName + "'")
        try:
            baud = int(connectionParams['baudrate'])
        except:
            raise ValueError("Unable to convert 'BaudRate' parameter " +
                    connectionParams['baudrate'] + "to an integer for " +
                    "serial device '" + deviceName + "'")
    else:
        raise ValueError("Unknown device_interface '" + deviceInterface +
                "' for device '" + deviceName + "'")

    #  extract the optional parameters and if missing provide sane defaults
    parseType = str(connectionParams.get('parsetype', 'None'))
    parseExp = str(connectionParams.get('parseexpression', ''))
    parseIndex = int(connectionParams.get('parseindex', 0))
    cmdPrompt = str(connectionParams.get('commandprompt', ''))

    #  if this device is configured for regex parsing, get the parse expression
    if (parseType.lower() == 'regex'):
        if 'parseexpression' not in connectionParams:
            raise ValueError("The required 'ParseExpression' parameter required for " +
                    "Regex parsing is missing for the device '" + deviceName +
                    "' in the device_configuration table")
        parseExp = connectionParams['parseexpression']

    return (deviceName, port, baud, parseType, parseExp, parseIndex, cmdPrompt)





