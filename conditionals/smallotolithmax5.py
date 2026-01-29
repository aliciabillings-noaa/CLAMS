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
    :module:: SmallOtolithMax5

    :synopsis: SmallOtolithMax5 a conditional that checks if a fish is smaller than 
    a threshold then counts the number of otoliths taken, after 5, otolith protocol stops

| Developed by:  Kelsey James <kelsey.james@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Southwest Fisheries Science Center (SWFSC)
| Fisheries Resources Division (FRD)
|
| Author:
|       Kelsey James <kelsey.james@noaa.gov>
| Maintained by:
|       Kelsey James <kelsey.james@noaa.gov>
        Melina Shak <melina.shak@noaa.gov>
"""
import unittest
import json

from PyQt6.QtCore import *


class SmallOtolithMax5(QObject):

    def __init__(self, db, schema, speciesCode, parent=None):
        '''
            The init methods of CLAMS validations are run whenever a new protocol
            or species is selected in the specimen module. Any setup that the
            validation requires should be done here. The three input arguments are:

                db - a reference to the active dbConnection class object
                speciesCode - the species code of the current specimen
                subcategory - the subcategory of the current specimen

            If you need to pass additional data to a validation, you should
            add this data to the species_data table and query it out here in
            the init method (see LengthRange.py for example.)
        '''

        #  call the superclass init
        QObject.__init__(self, None)

        #  Get the large length for this species from the species_data table
        sql = ("SELECT parameter_value FROM " + schema + ".species_data WHERE species_code=" + speciesCode +
               " AND lower(species_parameter)='small_length'")
        query = db.dbQuery(sql)
        smallLength, = query.first()

        # TODO define sample id dynamically
        sql = ("SELECT count(*) FROM " + schema + ".measurements WHERE measurement_type='alpha_barcode' " +
            "AND specimen_id in (SELECT specimen_id FROM " + schema + ".measurements WHERE " +
            "measurement_type='standard_length_mm' AND cast(measurement_value as float) < " + 
            smallLength + " AND sample_id=" + parent.activeSample + ")")
        query = db.dbQuery(sql)
        smallOtoCount, = query.first()
        
        #  extract returned results
        self.smallLength=float(smallLength)
        self.smallOtoCount=int(smallOtoCount)


    def evaluate(self,   measurements,  values,  result):
        '''
            The evaluate method is called when a measurement is taken to determine
            what changes in the protocol. Each measurement can have from 0-N validations. When
            a specific measurement is made, say "barcode", all validations
            assigned to the barcode measurement will have their validate methods
            called. Each one should verify that the currentValue is valid based
            on the logic of each particular validation.

                measurements - a list of the measurement types for this
                    protocol, in order.
                values - a list of the stored values of those measurements.
                    In order of the measurements.
                result -

        '''
        standardLen = values[measurements.index('standard_length_mm')]

        # check if the length is larger than the species 'largeLength', if yes, Otolith barcode is mandatory
        if standardLen and float(standardLen) < self.smallLength:
            if self.smallOtoCount >= 5:
                try:
                    result[measurements.index('alpha_barcode')]=[False, False]
                except:
                    pass
            else:
                try:
                    result[measurements.index('alpha_barcode')]=[True, True]
                except:
                    pass

        return result
       
