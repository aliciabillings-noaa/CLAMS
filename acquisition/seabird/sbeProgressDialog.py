#!/usr/bin/env python

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from .ui import ui_sbeProgressDialog


class sbeProgressDialog(QDialog, ui_sbeProgressDialog.Ui_sbeProgressDialog):

    def __init__(self, sbeObject, parent=None):
        super(sbeProgressDialog, self).__init__(parent)
        self.setupUi(self)

        self.sbe = sbeObject
        self.sbe.SBEProgress.connect(self.updateProgress)
        self.sbe.SBEAbort.connect(self.abortComplete)

        self.setWindowTitle(self.sbe.deviceName + ' Download Progress')
        self.progressBar.setValue(0)
        self.abortButton.clicked.connect(self.abort)


    def updateProgress(self, device, pct):
        self.progressBar.setValue(int(round(pct)))

    def abort(self):
        self.sbe.abort()

    def abortComplete(self):
        self.reset()
        self.hide()

    def reset(self):
        self.progressBar.setValue(0)
