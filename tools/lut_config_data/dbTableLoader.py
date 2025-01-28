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
.. module::dbTableLoader

    :synopsis: dbTableLoader is a simple class that uses dbConnection to
               either export a single table to .csv OR import a table from
               .csv. It does not handle constraint management and only does
               basic checks on the data types when importing. When inserting,
               it does not use prepared queries due to limitations of either
               Qt or the Oracle ODBC driver

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
import csv
from PyQt6 import QtCore
import dbConnection


class dbTableLoader(QtCore.QObject):

    #  define PyQt Signals
    stopped = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str, str)
    info = QtCore.pyqtSignal(str, str)

    def __init__(self, db, mode, dataPath, table,
            queryInterval=2, schema=None, whereClause=None):
        super(dbTableLoader, self).__init__()

        #  initialize some attributes
        self.dataPath = os.path.normpath(dataPath)
        self.db = db
        self.mode = mode.lower()
        self.table = table.lower()
        self.queryInterval = queryInterval
        self.schema = schema
        self.whereClause = whereClause
        self.csvfh = None
        self.csvFile = None
        self.nRows = 0
        self.stringCols = []


    @QtCore.pyqtSlot()
    def StartLoader(self):
        '''

        '''

        self.info.emit(self.table, 'Starting loader...')

        #  make sure the table exists
        try:
            sql = "SELECT * FROM " + self.schema + "." + self.table
            if self.whereClause:
                sql += " " + self.whereClause
            self.results = self.db.dbQuery(sql)
        except dbConnection.SQLError as e:
            self.error.emit(self.table, "Table doesn't exist or WHERE clause is bad (if provided): " + e.error)
            self.stopped.emit(self.table)
            return

        #  set up the filename
        self.datafile = self.dataPath + os.sep + self.table + ".csv"

        #  check the mode and our source/dest directory
        if self.mode == 'import':
            #  import, make sure the source directory + file exists
            if not os.path.exists(self.datafile):
                self.error.emit(self.table, "Source data file does not exist: " + self.datafile)
                self.stopped.emit(self.table)
                return

            #  try to open the source file
            try:
                self.csvfh = open(self.datafile, 'r')
                self.csvFile = csv.reader(self.csvfh, dialect=csv.unix_dialect)
            except Exception as e:
                self.error.emit(self.table, "Error opening source file " + self.datafile + " : " + str(e))
                self.stopped.emit(self.table)
                return

            # get the headers
            fileHeaders = next(self.csvFile)

            #  check if we have the same number of columns in both the source file and dest table
            if len(fileHeaders) != self.results.nColumns:
                self.error.emit(self.table, "Numer of columns in table (" + str(self.results.nColumns) +
                        ") does not match the number of columns in the source data file (" +
                        str(len(fileHeaders)) + "). Source file: " + self.datafile)
                self.stopped.emit(self.table)
                return

            #  check to make sure the table and file column names match
            headerCheck = [False] * self.results.nColumns
            for i, col in enumerate(fileHeaders):
                if col.lower() in self.results.columns:
                    headerCheck[i] = True
            if False in headerCheck:
                self.error.emit(self.table, "Column names in table (" + ','.join(self.results.columns) +
                        ") do not match the column names in the source data file (" +
                        ','.join(fileHeaders) + "). Source file: " + self.datafile)
                self.stopped.emit(self.table)
                return

            #  determine the columns that contain strings so we can quote them when inserting
            self.stringCols = [False] * self.results.nColumns
            for i, type in enumerate(self.results.columnTypes):
                if 'string' in type.lower():
                    self.stringCols[i] = True

            #  build the base SQL insert string
            self.SQLInsertStr = ("INSERT INTO " + self.schema + "." + self.table + " (" +
                    ','.join(fileHeaders) + ") VALUES (")

            #  all inserts are done as a trasaction so we start the transaction here
            self.db.startTransaction()


        elif self.mode == 'export':
            #  exporting, make sure export directory exists
            if not os.path.exists(self.dataPath):
                self.error.emit(self.table, "Destination data directory does not exist.")
                self.stopped.emit(self.table)
                return

            #  try to open the source file and write the header
            try:
                self.csvfh = open(self.datafile, 'w')
                self.csvFile = csv.writer(self.csvfh, dialect=csv.unix_dialect)
                # write the header
                self.csvFile.writerow(self.results.columns)
            except Exception as e:
                self.error.emit(self.table, "Error opening output file " + self.datafile + " : " + str(e))
                self.stopped.emit(self.table)
                return

        else:
            #  unknown mode
            self.error.emit(self.table, "Unknown mode '" + str(self.mode) + "'.")
            self.stopped.emit(self.table)
            return

        #  set up the timer that will
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.DoRow)
        self.timer.start(0)


    @QtCore.pyqtSlot()
    def DoRow(self):

        if self.mode == 'export':
            try:
                rowData = self.results.__next__()
                self.csvFile.writerow(rowData)
                self.nRows += 1
            except StopIteration:
                #  we're done with this table
                self.Stop()
                return
            except Exception as e:
                self.error.emit(self.table, "Error exporting to .csv file: " + str(e))
                self.stopped.emit(self.table)
                return
        else:

            try:
                #  build a list of values ready to insert for this row. Mostly this
                #  is just quoting string based columns, but we also need to handle
                #  NULL columns
                vals = []
                row = next(self.csvFile)
                for i, col in enumerate(row):
                    #  if this is a string column, we need to put quotes around the string
                    if self.stringCols[i]:
                        if col is None:
                            #  None is inserted as NULL
                            vals.append('NULL')
                        else:
                            #  quote strings and "escape" single quotes
                            vals.append("'" + col.replace("'", "''") + "'")
                    else:
                        #  empty numerical values or Nones are inserted as NULL
                        if col == '' or col is None:
                            vals.append('NULL')
                        else:
                            vals.append(col)

                sql = self.SQLInsertStr + ','.join(vals) + ")"

                #self.db.dbExec(sql)
                self.nRows += 1

                print(sql)

            except StopIteration:
                #  we're done with this table
                try:
                    self.db.commit()
                except Exception as e:
                    self.error.emit(self.table, "Error commiting import data to database!?!: " + str(e))
                self.Stop()
                return
            except Exception as e:
                self.error.emit(self.table, "Error importing from .csv file: " + str(e))
                self.db.rollback()
                self.error.emit(self.table, "Changes rolled back.")
                self.stopped.emit(self.table)
                return

        self.timer.start(self.queryInterval)


    @QtCore.pyqtSlot()
    def Stop(self):

        self.info.emit(self.table, "Table finished. Processed " + str(self.nRows) + " rows.")

        #  stop the timer
        self.timer.stop()

        #  discard results
        self.results = None

        #  close the csv file
        self.csvfh.close()

        self.stopped.emit(self.table)
