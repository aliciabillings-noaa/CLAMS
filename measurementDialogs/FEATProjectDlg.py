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
.. module:: FEATProjectDlg

    :synopsis: Special dialog to select a project to collect a whole fish, enter into the database, and print label

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assessment and Conservation Engineering Group (MACE)
|
| Author:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
| Maintained by:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
|       Mike Levine   <mike.levine@noaa.gov>
|       Nathan Lauffenburger   <nathan.lauffenburger@noaa.gov>
| Created by:
|       Alicia Billings - alicia.billings@noaa.gov
|       date: April 2019
| Updated February 2025 by:
|       Alicia Billings <alicia.billings@noaa.gov>
|           specific updates:
|               - PyQt import statement
|               - signal/slot connections
|               - added some function explanation
|               - fixed any PEP8 issues
|               - added a main to test if works (commented out)
|
| NOTE: cannot test this until it is called with parent values
"""

from PyQt6.QtWidgets import *
from PyQt6.QtGui import QIcon
import os
import pandas as pd
from datetime import datetime as dt
import numpad
import messagedlg


class FEATProjectDlg(QDialog):
    def __init__(self, parent=None):
        super(FEATProjectDlg, self).__init__(parent)
        self.db = parent.db
        self.activeSpcCode = parent.activeSpcCode
        self.activeSampleKey = parent.activeSampleKey
        self.activeHaul = parent.activeHaul
        self.settings = parent.settings
        self.errorSounds = parent.errorSounds
        self.errorIcons = parent.errorIcons
        self.workStation = parent.workStation
        self.survey = parent.survey
        self.ship = parent.ship
        self.activePartition = parent.activePartition
        self.backLogger = parent.backLogger
        self.scientist = parent.scientist

        self.numpad = numpad.NumPad()
        self.message = messagedlg.MessageDlg()

        self.collected_num = 0
        self.project = ""
        self.specimenKey = 0
        self.code = 0
        self.tot_allowed_num = 0
        self.tot_collected = 0
        self.tot_allowed_leg = 0
        self.leg_collected = 0
        self.tot_allowed_tow = 0
        self.tow_collected = 0

        # todo: at some point it would be nice to be able to read in the legs for a project in case there
        #  are different ones depending on which leg as well as get the samples already taken for each leg

        # set up the window
        title = "Which Project?"
        win_icon = QIcon()
        win_icon.addFile(self.settings['IconDir'] + "/giant_clam.ico")

        self.setWindowTitle(title)
        self.setFixedWidth(350)
        self.setFixedHeight(300)
        self.setWindowIcon(win_icon)

        self.overall_layout = QVBoxLayout()

        # add the instruction label
        instruction_label = QLabel()
        instruction_label.setStyleSheet("color: rgb(0, 0, 127); font: 14pt 'Calibri';")
        instruction_label.setText("Choose project to print label for...")
        self.overall_layout.addWidget(instruction_label)

        # add buttons for the projects
        # get the projects
        proto_sql = "SELECT protocol_name, label FROM Protocol_Definitions " \
                    "WHERE measurement_type = 'specimen_collection' AND " \
                    "protocol_name IN (SELECT protocol_name FROM Protocol_Map " \
                    "WHERE species_code IN (-1, " + self.activeSpcCode + ") AND active = 1 " \
                                                                         "GROUP BY protocol_name HAVING COUNT(*) = 1)"
        proto_query = self.db.dbQuery(proto_sql)
        while proto_query.next():
            # check conditionals
            proto_name = proto_query.value(0).toString()
            chk = self.check_conditionals(proto_name)
            if chk:
                btn = QPushButton()
                btn.setStyleSheet("color: rgb(0, 0, 127); font: 16pt 'Calibri';")
                btn.setText(proto_query.value(1).toString())
                btn.clicked.connect(self.set_project)
                self.overall_layout.addWidget(btn)

        self.setLayout(self.overall_layout)

        self.exec()

    def check_conditionals(self, protocol_name):
        """
        checks any conditionals for the protocol and species
        :param: name of the protocol to check with the species for the conditional
        :return: true or false
        """
        # load up the excel sheet for this project from the species_projects.xlsx into dataframe
        # read in the csv
        up_dir = os.path.abspath(os.curdir)
        proj_loc = up_dir + "\\resources\\special_projects.xlsx"

        try:
            proj_df = pd.read_excel(proj_loc, str(protocol_name), header=0)
            # get the row for the species code
            cur_row = proj_df[proj_df['Sp_code'].astype(int) == int(self.activeSpcCode)]
            # get the total numbers allowed
            self.tot_allowed_num = cur_row.iloc[0]['Num']
            self.tot_allowed_leg = cur_row.iloc[0]['num/leg']
            self.tot_allowed_tow = cur_row.iloc[0]['num/tow']

            # get the total already entered for the protocol for this species for this tow
            self.tow_collected = 0
            tow_sql = "SELECT measurement_value FROM Measurements WHERE sample_id = " + self.activeSampleKey + \
                      " AND measurement_parameter = 'collected_number' AND specimen_id IN " \
                      "(SELECT specimen_id FROM Specimen WHERE protocol_name = '" + protocol_name + \
                      "' AND event_id = " + self.activeHaul + ")"
            tow_query = self.db.dbQuery(tow_sql)
            while tow_query.next():
                self.tow_collected += int(tow_query.value(0).toString())

            # get the total already entered for the protocol for this species for the cruise
            self.tot_collected = 0
            tot_coll_sql = "SELECT measurement_value FROM Measurements WHERE " \
                           "measurement_parameter = 'collected_number' AND survey = " + self.survey + \
                           " AND specimen_id IN " \
                           "(SELECT specimen_id FROM Specimen WHERE protocol_name = '" + protocol_name + "')"
            tot_query = self.db.dbQuery(tot_coll_sql)
            while tot_query.next():
                self.tot_collected += int(tot_query.value(0).toString())
            if (self.tot_collected >= self.tot_allowed_num) or (self.leg_collected >= self.tot_allowed_leg) \
                    or (self.tow_collected >= self.tot_allowed_tow):
                rtn = False
            else:
                rtn = True
        except:
            # if there is no sheet for the project, assume there are no limits and return True
            rtn = True

        return rtn

    def set_project(self):
        """
        sets the project, pushes up number pad to enter number of specimens collected, enters the record
        into the database, and closes the dialog with accept
        :return:
        """
        self.project = "FEAT " + self.sender().text()
        self.numpad.msgLabel.setText("Enter number collected...")
        if not self.numpad.exec():
            #  user cancelled action
            return
        #  get the number from the numpad
        val = self.numpad.value
        #  check that we didn't get a 0 value
        if val == '0':
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                    "You have entered 0 (zero) for the number collected, which is not allowed. "
                                    "Please enter a valid number.", 'info')
            self.message.exec()
        else:
            self.collected_num = val
            # enter into the database
            # get the protocol name
            proto_sql = "SELECT protocol_name FROM Protocol_Definitions WHERE label = '" + self.sender().text() + "'"
            proto_query = self.db.dbQuery(proto_sql)
            proto_query.first()
            protocol_name = proto_query.value(0).toString()
            # get the current date
            cur_date = dt.strftime(dt.now(), "%d-%b-%y")
            # enter a new specimen
            insert_vals = "(" + self.ship + "," + self.survey + "," + self.activeHaul + "," + self.activeSampleKey + \
                          "," + self.workStation + ",'" + self.scientist + "','random','" + protocol_name \
                          + "','" + cur_date + "')"
            insert_txt = "INSERT INTO SPECIMEN (Ship, Survey, Event_Id, Sample_Id, Workstation_Id, " \
                         "Scientist, Sampling_Method, Protocol_Name, Time_Stamp) VALUES %s" % insert_vals
            try:
                self.db.dbQuery(insert_txt)
            except Exception as e:
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2], 'Problem inserting the record into '
                                                                                 'the Specimen table:'
                                                                                 ' ' + str(e), 'info')
                self.message.exec()

            # get the newly created specimen key
            spec_sql = "SELECT max(specimen_id) FROM specimen WHERE ship=" + self.ship + " AND survey=" + self.survey \
                       + " AND event_id=" + self.activeHaul + " AND sample_id=" + self.activeSampleKey + \
                       " AND workstation_id=" + self.workStation
            spec_query = self.db.dbQuery(spec_sql)
            spec_query.first()
            spec_key = spec_query.value(0).toString()
            # create barcode
            self.code = str(self.survey) + str(self.ship) + str(self.activeHaul) + str(spec_key) + \
                        str(self.collected_num)
            # enter a new measure for the collection AND the collected number
            all_vals = self.ship + "," + self.survey + "," + self.activeHaul + "," + self.activeSampleKey + \
                       "," + spec_key
            vals_1 = "(" + all_vals + ",'specimen_collection','" + self.code + "',0)"
            meas_txt_1 = "INSERT INTO Measurements (Ship, Survey, Event_Id, Sample_Id, Specimen_Id, " \
                         "Measurement_Type, Measurement_Value, Device_Id) VALUES %s" % vals_1
            try:
                self.db.dbQuery(meas_txt_1)
            except Exception as e:
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2], 'Problem inserting the record into '
                                                                                 'the Measurements table:'
                                                                                 ' ' + str(e), 'info')
                self.message.exec()
            vals_2 = "(" + all_vals + ",'collected_number'," + str(self.collected_num) + ",0)"
            meas_txt_2 = "INSERT INTO Measurements (Ship, Survey, Event_Id, Sample_Id, Specimen_Id, " \
                         "Measurement_Type, Measurement_Value, Device_Id) VALUES %s" % vals_2
            try:
                self.db.dbQuery(meas_txt_2)
            except Exception as e:
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2], 'Problem inserting the record into '
                                                                                 'the Measurements table:'
                                                                                 ' ' + str(e), 'info')
                self.message.exec()
            self.accept()

    def closeEvent(self, event):
        self.reject()
