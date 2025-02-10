"""
updated November 2022 to PyQt6 and Python 3 by Alicia Billings, NWFSC
specific updates:
- PyQt import statements
- added some function explanation
- fixed any PEP8 issues
- added a main to test if works (commented out)

todo: test this when able to connect to db
"""

from PyQt6.QtWidgets import *
from PyQt6.QtSql import QSqlQuery
from ui.xga import ui_MatSelDlg
import matguide


class MatSelDlg(QDialog, ui_MatSelDlg.Ui_matselDlg):
    def __init__(self,  parent=None):
        super(MatSelDlg, self).__init__(parent)
        self.setupUi(self)
        self.db = parent.db
        self.settings = parent.settings
        self.speciesName = parent.activeSpcName
        self.activeSpcCode = parent.activeSpCode

        # variable declarations
        self.result = ()
        self.buttons = [self.mat1Btn, self.mat2Btn, self.mat3Btn, self.mat4Btn, self.mat5Btn, self.mat6Btn,
                        self.mat7Btn, self.mat8Btn]
        # used for NWFSC
        self.oto_present = True

        # get maturity stage names
        query0 = QSqlQuery("SELECT parameter_value FROM species_data "
                           "WHERE lower(species_parameter)='maturity_table' AND species_code=" + self.activeSpcCode)
        if not query0.first():
            return

        query = QSqlQuery("SELECT md.button_text, md.description_text_female "
                          "FROM maturity_description AS md, maturity_tables AS mt "
                          "WHERE (mt.maturity_table = md.maturity_table) AND "
                          "(mt.maturity_table = " + query0.value(0).toString() + ")")
        maturityBtnText = []

        while query.next():
            maturityBtnText.append(query.value(0).toString())

        # signal/slot connections
        self.guideBtn.clicked.connect(self.getGuide)
        for btn in self.buttons:
            btn.clicked.connect(self.getMat)
            try:
                btn.setText(maturityBtnText[self.buttons.index(btn)])
            except:
                btn.setText(' -  ')
                btn.setEnabled(False)

    def setup(self, parent):
        pass

    def getMat(self):
        self.result = (True, self.sender().text())
        self.accept()

    def getGuide(self):
        matGuide = matguide.MatGuide(self)
        matGuide.exec()

    def closeEvent(self, event):

        self.result =  (False, '')
        self.reject()


"""
if __name__ == "__main__":
    #  create an instance of QApplication
    app = QApplication(argv)
    #  create an instance of the dialog
    form = GeneticYesNoDlg()
    #  show it
    form.show()
    #  and start the application...
    app.exec()
"""