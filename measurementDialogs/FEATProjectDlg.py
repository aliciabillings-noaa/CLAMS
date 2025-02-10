"""
Special dialog to select project to print label for

created by: Alicia Billings - alicia.billings@noaa.gov
date: April 2019
notes:
"""

from PyQt4.QtGui import *
from PyQt4 import QtSql
from PyQt4.QtCore import *
import os
import pandas as pd
from datetime import datetime as dt
import numpad
import messagedlg
import functions as fun


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

        # read in leg csv
        #up_dir = os.path.abspath(os.curdir)
        #leg_loc = up_dir + "\\resources\\legs.csv"
        #self.leg_df = pd.read_csv(leg_loc)
        self.leg_df = fun.get_legs()

        # get the start and end date for the current leg
        cur_date = int(dt.strftime(dt.now(), "%Y%m%d"))
        # get start and end date for the leg
        dates = self.leg_df.loc[(self.leg_df['start'].astype(int) <= cur_date) &
                                (self.leg_df['end'].astype(int) >= cur_date), ['start', 'end']]
        start = dates.iloc[0][0]
        end = dates.iloc[0][1]

        # get the sample numbers for the current leg
        samples = []
        sample_query_txt = "SELECT sample_id FROM Samples WHERE parent_sample IS NOT NULL AND event_id IN " \
                           "(SELECT event_id FROM Event_Data WHERE event_parameter = 'EventOverallDate' " \
                           "AND parameter_value BETWEEN '" + str(start) + "' AND '" + str(end) + "')"
        sample_query = QtSql.QSqlQuery(sample_query_txt)
        while sample_query.next():
            samples.append(sample_query.value(0).toString())
        self.smp_lst = ",".join(str(s) for s in samples)

        # set up the window
        title = "Which Project?"
        win_icon = QIcon()
        win_icon.addFile(self.settings[QString('IconDir')] + "/giant_clam.ico")

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
        query_txt = "SELECT protocol_name, label FROM Protocol_Definitions "\
                    "WHERE measurement_type = 'specimen_collection' AND "\
                    "protocol_name IN (SELECT protocol_name FROM Protocol_Map "\
                    "WHERE species_code IN (-1, " + self.activeSpcCode + ") AND active = 1 "\
                    "GROUP BY protocol_name HAVING COUNT(*) = 1)"
        query = QtSql.QSqlQuery(query_txt)
        while query.next():
            # check conditionals
            proto_name = query.value(0).toString()
            chk = self.check_conditionals(proto_name)
            if chk:
                btn = QPushButton()
                btn.setStyleSheet("color: rgb(0, 0, 127); font: 16pt 'Calibri';")
                btn.setText(query.value(1).toString())
                btn.clicked.connect(self.set_project)
                self.overall_layout.addWidget(btn)

        self.setLayout(self.overall_layout)

        self.exec_()

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
            tow_query_txt = "SELECT measurement_value FROM Measurements WHERE sample_id = " + self.activeSampleKey + \
                            " AND measurement_parameter = 'collected_number' AND specimen_id IN " \
                            "(SELECT specimen_id FROM Specimen WHERE protocol_name = '" + protocol_name \
                            + "' AND event_id = " + self.activeHaul + ")"
            tow_query = QtSql.QSqlQuery(tow_query_txt)
            while tow_query.next():
                self.tow_collected += int(tow_query.value(0).toString())

            # get the total already entered for the protocol for this species for this leg
            self.leg_collected = 0
            leg_query_txt = "SELECT measurement_value FROM Measurements WHERE sample_id IN (" + self.smp_lst + \
                            " AND measurement_parameter = 'collected_number' AND specimen_id IN " \
                            "(SELECT specimen_id FROM Specimen WHERE protocol_name = '" + protocol_name + "')"
            leg_query = QtSql.QSqlQuery(leg_query_txt)
            while leg_query.next():
                self.leg_collected += int(leg_query.value(0).toString())

            # get the total already entered for the protocol for this species for the cruise
            self.tot_collected = 0
            tot_query_txt = "SELECT measurement_value FROM Measurements WHERE " \
                            "measurement_parameter = 'collected_number' AND survey = " + self.survey + \
                            " AND specimen_id IN " \
                            "(SELECT specimen_id FROM Specimen WHERE protocol_name = '" + protocol_name + "')"
            tot_query = QtSql.QSqlQuery(tot_query_txt)
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
        finish = 0
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
            proto_txt = "SELECT protocol_name FROM Protocol_Definitions WHERE label = '" + self.sender().text() + "'"
            proto_query = QtSql.QSqlQuery(proto_txt)
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
                insert_query = QtSql.QSqlQuery(insert_txt)
            except Exception as e:
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2], 'Problem inserting the record into '
                                                                                 'the Specimen table:'
                                                                                 ' ' + str(e), 'info')
                self.message.exec()

            # get the newly created specimen key
            query = QtSql.QSqlQuery("SELECT max(specimen_id) FROM specimen WHERE ship=" + self.ship + " AND survey=" +
                                    self.survey + " AND event_id=" + self.activeHaul + " AND sample_id=" +
                                    self.activeSampleKey + " AND workstation_id=" + self.workStation)
            query.first()
            spec_key = query.value(0).toString()
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
                meas_query_1 = QtSql.QSqlQuery(meas_txt_1)
            except Exception as e:
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2], 'Problem inserting the record into '
                                                                                 'the Measurements table:'
                                                                                 ' ' + str(e), 'info')
                self.message.exec_()
            vals_2 = "(" + all_vals + ",'collected_number'," + str(self.collected_num) + ",0)"
            meas_txt_2 = "INSERT INTO Measurements (Ship, Survey, Event_Id, Sample_Id, Specimen_Id, " \
                         "Measurement_Type, Measurement_Value, Device_Id) VALUES %s" % vals_2
            try:
                meas_query_2 = QtSql.QSqlQuery(meas_txt_2)
            except Exception as e:
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2], 'Problem inserting the record into '
                                                                                 'the Measurements table:'
                                                                                 ' ' + str(e), 'info')
                self.message.exec_()
            self.accept()

    def closeEvent(self, event):
        self.reject()
