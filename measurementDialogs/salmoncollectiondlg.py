
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from ui import ui_SalmonCollection

class SalmonCollectionDlg(QDialog, ui_SalmonCollection.Ui_salmoncollectionDlg):
    def __init__(self,  parent=None):
        super(SalmonCollectionDlg, self).__init__(parent)
        self.setupUi(self)
        self.fins = []

        self.buttons = [self.Btn1,  self.Btn2,  self.Btn3,  self.Btn4,  self.Btn5,  self.Btn6,  self.Btn7]
        btn_text = ['None',  'Adipose',  'Pectoral',  'Pelvic',  'Anal',  'Dorsal',  'Caudal']
        for i in range(len(self.buttons)):
            self.buttons[i].setText(btn_text[i])
            self.buttons[i].clicked.connect(self.select)
            self.buttons[i].setEnabled(True)            
        self.doneBtn.clicked.connect(self.Enter)
        self.clearBtn.clicked.connect(self.Clear)

    def setup(self, parent):        
        pass        

    def select(self):
        fin_result = (str(self.sender().text()))
        print(fin_result)
        self.fins.append(fin_result)
        print(self.fins)
        
    def Clear(self):
        for i in range(len(self.buttons)):           
            self.buttons[i].setChecked(False)
            self.fins = []

    def Enter(self): 
        
        self.fins = []
        for button in self.buttons: 
            if button.isChecked():
                #  check if None is selected, if so we return none and ignore everything else
                if str(button.text()).lower() == 'none':
                    self.fins = ['None']
                    break
                self.fins.append(str(button.text()))
        print(self.fins)
        
        # if there's no entry- display warning 
        if not self.fins:
            QMessageBox.critical(self, "ERROR", "<font size = 12> You need to select a missing fin!")
        
        #otherwise get the result
        if self.fins:
            #  return the text
            self.result =   (True, ",".join(self.fins))
            self.accept()
            # reset the buttons
            for i in range(len(self.buttons)):           
                self.buttons[i].setChecked(False)
                self.fins = []


    def closeEvent(self, event):
        # query to clear and set new codes
        self.result = (False, '')
        self.reject()
