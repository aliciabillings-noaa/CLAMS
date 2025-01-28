#!/usr/bin/env python3
# coding=utf-8
#
#     National Oceanic and Atmospheric Administration (NOAA)
#     Alaskan Fisheries Science Center (AFSC)
#     Resource Assessment and Conservation Engineering (RACE)
#     Midwater Assessment and Conservation Engineering (MACE)
#
#  THIS SOFTWARE AND ITS DOCUMENTATION ARE CONSIDERED TO BE IN THE PUBLIC DOMAIN
#  AND THUS ARE AVAILABLE FOR UNRESTRICTED PUBLIC USE. THEY ARE FURNISHED "AS
#  IS."  THE AUTHORS, THE UNITED STATES GOVERNMENT, ITS INSTRUMENTALITIES,
#  OFFICERS, EMPLOYEES, AND AGENTS MAKE NO WARRANTY, EXPRESS OR IMPLIED,
#  AS TO THE USEFULNESS OF THE SOFTWARE AND DOCUMENTATION FOR ANY PURPOSE.
#  THEY ASSUME NO RESPONSIBILITY (1) FOR THE USE OF THE SOFTWARE AND
#  DOCUMENTATION; OR (2) TO PROVIDE TECHNICAL SUPPORT TO USERS.
#
"""
.. module::

    :synopsis:

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
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
import os
import sys
import yaml
import logging
import argparse
from PyQt6 import QtCore
import dbTableLoader
import dbConnection


class CLAMSTableLoader(QtCore.QObject):


    #  define PyQt Signals
    stopRunning = QtCore.pyqtSignal()
    stopLoader = QtCore.pyqtSignal()


    def __init__(self, configFile, parent=None):
        super(CLAMSTableLoader, self).__init__(parent)

        self.threads = {}
        self.loaders = {}
        self.nTablesProcessed = 0
        self.nThreads = 0
        self.stopping = False
        self.logLevel = logging.INFO

        #  initialize some attributes
        self.configFile = os.path.normpath(configFile)

        #  connect the stop signal to our stop method
        self.stopRunning.connect(self.Stop)

        #  start things up after we get the event loop running by using a timer
        QtCore.QTimer.singleShot(0, self.InitApplication)


    def InitApplication(self):
        '''

        '''

        required_params = ['mode',
                           'odbc_data_source',
                           'username',
                           'password',
                           'schema',
                           'query_interval',
                           'where_clause',
                           'data_path',
                           'tables',
                           'n_threads']

        #  bump the cursor
        print()

        #  create a logger to log to the console
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.logLevel)
        formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(module)s - %(message)s')
        consoleLogger = logging.StreamHandler(sys.stdout)
        consoleLogger.setFormatter(formatter)
        self.logger.addHandler(consoleLogger)

        self.logger.info("Starting CLAMSTableLoader...")
        self.logger.info("Reading config file: " + self.configFile)

        #  read the configuration file
        with open(self.configFile, 'r') as cf_file:
            try:
                config = yaml.safe_load(cf_file)
            except yaml.YAMLError as exc:
                self.logger.error('Error reading configuration file ' + self.configFile)
                self.logger.error('    Error string:' + str(exc))
                self.logger.error("Application exiting...")
                QtCore.QCoreApplication.instance().quit()
                return

        #  make sure we have all of our params and add them as attributes
        for param in required_params:
            if param in config:
                setattr(self, param, config[param])
            else:
                self.logger.error("Configuration parameter '" + param +
                        "' not specified in configuration file: " + self.configFile)
                QtCore.QCoreApplication.instance().quit()
                return


        #  establish database connection
        try:
            self.db = dbConnection.dbConnection(self.odbc_data_source, self.username, self.password,
                    label='TableLoader')
            self.db.dbOpen()
        except dbConnection.SQLError as e:
            self.logger.error("Couldn't connect to database: " + e.error)
            QtCore.QCoreApplication.instance().quit()
            return

        #  start the initial loader threads
        for n in range(self.n_threads):
            try:
                table = self.tables.pop()
                self.StartTableThread(table)
            except IndexError:
                pass
            except Exception as e:
                raise e


    def StartTableThread(self, table):

        self.logger.info("Starting " + self.mode + " of table: " + table)

        #  create a thread for this tableLoader
        thread = QtCore.QThread(self)
        self.threads[thread] = thread

        #  create an instance of dbTableLoader
        tableLoader = dbTableLoader.dbTableLoader(self.db, self.mode, self.data_path,
                table, queryInterval=self.query_interval, schema=self.schema,
                whereClause=self.where_clause)
        self.loaders[thread] = tableLoader

        #  move the tableLoader to that thread
        tableLoader.moveToThread(thread)

        #  connect up our signals
        tableLoader.error.connect(self.LoaderError)
        tableLoader.stopped.connect(self.LoaderStopped)
        tableLoader.info.connect(self.LoaderMessage)
        self.stopLoader.connect(tableLoader.Stop)
        self.stopRunning.connect(self.Stop)
        thread.started.connect(tableLoader.StartLoader)

        #  these signals handle the cleanup when we're done
        tableLoader.stopped.connect(thread.quit)
        thread.finished.connect(self.threadCleanup)

        #  and start the thread
        thread.start()

        #  increment the tables processed counter
        self.nTablesProcessed += 1
        self.nThreads += 1


    @QtCore.pyqtSlot(str, str)
    def LoaderMessage(self, table_name, message):
        self.logger.info(table_name + " ::: " + message)


    @QtCore.pyqtSlot(str, str)
    def LoaderError(self, table_name, message):
        self.logger.error(table_name + " ::: " + message)


    @QtCore.pyqtSlot()
    def threadCleanup(self):

        #  get a reference to the thread that is shutting down
        thread = QtCore.QObject.sender(self)

        if thread in self.threads:

            #  delete the reference to the thread
            del self.threads[thread]
            del self.loaders[thread]

            self.logger.debug("Bits deleted.")


    @QtCore.pyqtSlot(str)
    def LoaderStopped(self, table_name):

        self.logger.debug(table_name + " ::: Loader stopped.")

        self.nThreads -= 1

        if self.stopping:
            self.logger.debug("Been told to stop")

            if len(self.threads) == 0:
                self.Stop(finished=True)
        else:
            self.logger.debug("Tables left: " + str(len(self.tables)))
            if len(self.tables) > 0:
                self.logger.debug("Threads running: " + str(self.nThreads))
                if self.nThreads < self.n_threads:
                    try:
                        table = self.tables.pop()
                        self.StartTableThread(table)
                    except IndexError:
                        pass
                    except Exception as e:
                        raise e
            else:
                if self.nThreads == 0:
                    self.Stop(finished=True)


    @QtCore.pyqtSlot()
    def Stop(self, finished=False):

        if not finished:
            self.logger.info("Starting to shut down CLAMSTableLoader. Terminating threads..")
            self.stopLoader.emit()
            self.stopping = True
        else:
            #  all threads finished

            self.db.dbClose()

            self.logger.info("Application exiting...")
            QtCore.QCoreApplication.instance().quit()
            return


    def external_stop(self):
        '''
        external_stop is called when one of the main thread exit handlers are called.
        It emits a stop signal that is then received by the QCoreApplication which then
        shuts everything down in the QCoreApplication thread.
        '''
        self.stopRunning.emit()



def exit_handler(a,b=None):
    '''
    exit_handler is called when CTRL-c is pressed on Windows
    '''
    global ctrlc_pressed

    if not ctrlc_pressed:
        #  make sure we only act on the first ctrl-c press
        ctrlc_pressed = True
        print("CTRL-C detected. Shutting down...")
        console_app.external_stop()

    return True


def signal_handler(*args):
    '''
    signal_handler is called when ctrl-c is pressed when the python console
    has focus. On Linux this is also called when the terminal window is closed
    or when the Python process gets the SIGTERM signal.
    '''
    global ctrlc_pressed

    if not ctrlc_pressed:
        #  make sure we only act on the first ctrl-c press
        ctrlc_pressed = True
        print("CTRL-C or SIGTERM/SIGHUP detected. Shutting down...")
        console_app.external_stop()

    return True


if __name__ == "__main__":

     #  create a state variable to track if the user typed ctrl-c to exit
    ctrlc_pressed = False

    #  Set up the handlers to trap ctrl-c
    if sys.platform == "win32":
        #  On Windows, we use win32api.SetConsoleCtrlHandler to catch ctrl-c
        import win32api
        win32api.SetConsoleCtrlHandler(exit_handler, True)
    else:
        #  On linux we can use signal to get not only ctrl-c, but
        #  termination and hangup signals also.
        import signal
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGHUP, signal_handler)

    #  parse the command line arguments
    parser = argparse.ArgumentParser(prog='CLAMSTableLoader', description='CLAMSTableLoader exports or imports ' +
            'data from/to CLAMS database tables.')

    #  specify the positional arguments: ODBC connection, username, password, mode, directory, table
    parser.add_argument("config_file", help="Set this to the path to the YAML file containing the " +
            "import/export configuration parameters.")

    #  parse our arguments
    args = parser.parse_args()
    config_file = os.path.normpath(str(args.config_file))

    #  create an instance of QCoreApplication and and instance of the our example application
    app = QtCore.QCoreApplication(sys.argv)
    console_app = CLAMSTableLoader(config_file, parent=app)

    #  and start the event loop
    sys.exit(app.exec())
