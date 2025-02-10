"""
BatchSummaryLoader.py

This script batch loads the clamsbase2.catch_summary table. See the bottom of the
script for parameters.
"""

import os
import sys
import signal
import logging
import datetime
from PyQt4 import QtCore
import dbConnection
import Clamsbase2Functions


running = True

class batch_catch(QtCore.QObject):

    def __init__(self, odbcSource, user, password, schema, surveyStart,
            surveyEnd, overwrite, ships, logDir):

        super(batch_catch, self).__init__()

        self.odbcSource = odbcSource
        self.user = user
        self.password = password
        self.schema = schema
        self.start = surveyStart
        self.end = surveyEnd
        self.ships = ships
        self.overwrite = overwrite
        self.log_dir = logDir
        #self.log_level = logging.DEBUG
        self.log_level = logging.INFO
        self.dry_run = False


        #  set a timer to kick things off
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.batchUpdate)
        timer.setSingleShot(True)
        timer.start(0)


    def batchUpdate(self):

        #  create an instance of our dbConnection
        self.db = dbConnection.dbConnection(self.odbcSource, self.user, self.password)
        self.db.bioSchema = self.schema

        #  get the application start time
        start_time_string = datetime.datetime.now().strftime("D%Y%m%d-T%H%M%S")

        try:
            logfile_name = os.path.normpath(self.log_dir + os.sep + start_time_string + '.log')

            #  make sure we have a directory to log into
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)

            #  create the logger
            self.logger = logging.getLogger()
            self.logger.setLevel(self.log_level)
            fileHandler = logging.FileHandler(logfile_name)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fileHandler.setFormatter(formatter)
            self.logger.addHandler(fileHandler)
            consoleLogger = logging.StreamHandler(sys.stdout)
            consoleLogger.setFormatter(formatter)
            self.logger.addHandler(consoleLogger)

        except:
            print("CRITICAL ERROR: Unable to create log file " + logfile_name)
            self.logger.error("Unable to create log file " + logfile_name)


        self.logger.info("Starting batch loading of the " + self.schema + ".catch_summary table...")

        #  open the connection - dbOpen will raise an error if it can't connect
        try:
            self.db.dbOpen()
        except Exception as err:
            self.logger.critical("Unable to open database:" + err)
            QtCore.QCoreApplication.instance().quit()

        # Create a dict to hold our surveys
        self.surveys = {}

        # Query all of the surveys and build a list of surveys we need to update
        self.logger.info("Looking for surveys to process:")
        self.logger.info("  Starting Survey:" + str(self.start))
        self.logger.info("  Ending Survey:" + str(self.end))
        self.logger.info("  Overwrite:" + str(self.overwrite))
        sql = ("SELECT survey,ship FROM " + self.schema + ".surveys WHERE survey>=" + str(self.start) +
                " AND survey<=" + str(self.end))
        survey_query = self.db.dbQuery(sql)
        for survey, ship in survey_query:
            if ship in self.ships or int(ship) in self.ships:
                # check if this survey has the source data
                sql = ("SELECT distinct(event_id) FROM " + self.schema + ".samples WHERE ship=" + ship + " AND survey=" + survey +
                        " AND sample_type='Species'")
                eventQuery = self.db.dbQuery(sql)
                survey_events = []
                for event, in eventQuery:
                    # Check for data for each event to pick up partially updated surveys
                    if not overwrite:
                        # now check if any data already exists
                        sql = ("SELECT survey FROM " + self.schema + ".catch_summary WHERE ship=" + ship + " AND survey="
                                + survey + " AND event_id=" + event)
                        dataQuery = self.db.dbQuery(sql)
                        if dataQuery.first()[0]:
                            # data exists for this survey and we're not overwriting so we skip it
                            self.logger.debug("Data exists for " + str(ship) + ":" + str(survey) + ":" + str(event) + " --- skipping.")
                            continue

                    # append this to our list of events to process
                    survey_events.append(event)

                # Check if we have any events to process for this survey
                if survey_events:
                    # We do - This is a survey we need to run
                    self.logger.info("Adding survey " + str(ship) + ":"+ str(survey) + " to list to process.")

                    # add that info to our dict
                    self.surveys[survey] = {'ship':ship, 'events':survey_events}

                else:
                    self.logger.debug("Nothing to update or no data exists for " + str(ship) + ":" + str(survey) + " --- skipping.")
            else:
                self.logger.debug("Skipping survey " + str(survey) + " because ship "+ str(ship) + " is not in our list of ships to process.")


        # Now work through our surveys
        for idx,  survey in enumerate(self.surveys):
            ship = self.surveys[survey]['ship']
            self.logger.info("Processing survey " + str(ship) + ":" + str(survey))
            # and the events in this survey
            for event in self.surveys[survey]['events']:

                if running:
                    self.updateCatchSummaryTable(ship, survey, event)
                else:
                    continue

        self.logger.info("Update finished!")
        QtCore.QCoreApplication.instance().quit()


    def updateCatchSummaryTable(self, ship, survey, event_id):
        '''
        updateCatchSummaryTable updates the catch summary data for the specified
        ship, survey, and event
        '''

        self.logger.info("    Processing Event " + event_id)

        #  set the initial return state
        ok = True

        #  create an instance of clamsbase functions
        clamsFunctions = Clamsbase2Functions.Clamsbase2Functions(self.db, ship, survey)

        #  delete existing data for this event
        if not self.dry_run:
            sql = ("DELETE FROM " + self.schema + ".catch_summary WHERE ship=" + ship +
                    " AND survey=" + survey + " AND event_id=" + event_id)
            self.db.dbExec(sql, forwardOnly=True)

        #  find all the unique species samples
        sql = ("SELECT sample_id, parent_sample, partition, species_code, subcategory FROM " +
                self.schema + ".samples " + "WHERE ship=" + ship + " AND survey=" + survey +
                " AND event_id=" + event_id + " AND sample_type='Species'")
        self.logger.debug("      Querying:" + sql)

        sampleQuery = self.db.dbQuery(sql, forwardOnly=True)
        for sample_id, parent_sample, partition, species_code, subcategory in sampleQuery:

            [status, vals] = clamsFunctions.computeCatchSummary(event_id, partition, species_code, subcategory)
            self.logger.debug("      Computed " + partition + ":" + species_code + ":" + subcategory + " --- status:" + str(status))

            #  check if we successfully computed the summary data
            if status:
                vals = vals[0]
                #  yes - get species name
                sql = ("SELECT scientific_name, common_name FROM " + self.schema +
                        ".species WHERE species_code=" + species_code)
                sppQuery = self.db.dbQuery(sql)
                sci_name, common_name = sppQuery.first()

                #  then insert results into catch summary table
                sql = ("INSERT INTO " + self.schema + ".catch_summary (ship,survey,event_id,partition,sample_id,parent_sample," +
                        "scientific_name,species_code,common_name,subcategory,weight_in_haul,sampled_weight," +
                        "number_in_haul,sampled_number,frequency_expansion,in_mix,whole_hauled) VALUES(" +
                        ship + "," + survey + "," + event_id + ",'" + partition + "'," + sample_id + "," +
                        parent_sample + ",'" + sci_name + "'," + species_code + ",'" + common_name +
                        "','" + subcategory + "'," + str(vals[4]) + "," + str(vals[5]) + "," +
                        str(vals[6]) + ","+str(vals[7]) + "," + str(vals[8]) + "," + str(vals[9]) +
                        "," + str(vals[10]) + ")")
                if not self.dry_run:
                    self.db.dbExec(sql, forwardOnly=True)

            else:
                #  check to make sure there is an actionable error - computeCatchSummary can return false if there
                #  is a sample with no measurements which we silently ignore here as it isn't necessarily an error
                if (len(vals) > 0):
                    self.logger.error("Error computing catch summary data for event " +
                            event_id + ". Error text:" + vals[2]  + vals[1])
                    ok = False
                    break


        return ok



def abort():
    '''
    abort has the analysis "parent" object emit the abort signal to
    stop macebase2computations
    '''
    global running
    running = False


if __name__ == "__main__":

    # Set up the starting and ending survey
    surveyStart = 199900
    surveyEnd = 202100

    # Specify a lists of ships to consider. Surveys on vessels not in this
    # list will be ignored.
    ships = [157, 21]

    # Specify if existing data should be overwritten. If false, and
    # a data exists for a survey+event, the survey+event will be skipped.
    overwrite = False

    # Specify a path to a folder where the log file will be written
    logDir = 'c:/temp/'

    # and the database parmeters
    odbcSource = 'afsc-64'
    database_user = 'clamsbase2'
    schema = 'clamsbase2'
    password = 'pollock#475'

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGINT, abort)

    app = QtCore.QCoreApplication(sys.argv)
    form = batch_catch(odbcSource, database_user, password, schema, surveyStart,
            surveyEnd, overwrite, ships, logDir)

    sys.exit(app.exec())

