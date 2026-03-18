"""
Checks the diet counts for the tow

Created by Alicia Billings alicia.billings@noaa.gov
date: April 2019
notes:
"""

from PyQt6.QtCore import *


class DietCheck(QObject):

    def __init__(self, db, schema, speciesCode, parent=None):
        #  call the superclass init
        QObject.__init__(self, None)
        self.db = db

        self.tot_collect = 10
        self.tot_called = 0
        self.collected = 0
        self.called = 0

    def evaluate(self, measurements, values, result):
        """
        checks to see if the diets are already collected
        :param measurements: available measurements for the specimen
        :param values: collected values for the specimen; not used in this conditional
        :param result: list of the measurement types and whether their buttons should be enabled
        :return: return the result list with any changes
        """
        # get current tow
        tow_query = QtSql.QSqlQuery("SELECT parameter_value FROM " + self.schema + ".Application_Configuration "
                                    "WHERE parameter = 'ActiveEvent'")
        tow_query.first()
        self.cur_tow = tow_query.value(0).toString()

        # get total already collected and called
        collection_query = QtSql.QSqlQuery("SELECT COUNT(*) FROM " + self.schema + ".Measurements WHERE event_id = " + self.cur_tow +
                                           " AND measurement_type = 'stomach_collect'"
                                           " AND measurement_value NOT IN ('Blown', 'Nicked', 'Regurg', 'Unknown')")
        collection_query.first()
        self.collected = int(collection_query.value(0).toString())

        # get total already collected and called
        called_query = QtSql.QSqlQuery("SELECT COUNT(*) FROM " + self.schema + ".Measurements WHERE event_id = " + self.cur_tow +
                                       " AND measurement_type = 'stom_cont_1'"
                                       " AND measurement_value NOT IN ('Blown', 'Nicked', 'Regurg', 'Unknown')")
        called_query.first()
        self.called = int(called_query.value(0).toString())
        if self.collected >= self.tot_collect and self.called >= self.tot_called:
            result[measurements.index('diet_collection')] = [False]

        return result
