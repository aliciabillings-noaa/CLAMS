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
.. module:: startMACETrawlEvent

    :synopsis: startMACETrawlEvent presents the event selection dialog
               allowing the user to select the event (new or previous) and
               then opens the trawl event form for that event. It used
               to also present the simple protected spp. check dialog but
               that was disabled starting with the FY22 field season since
               the PS observation protocol changed and the observation
               start and stop actions were integrated into our trawl events.

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
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

import MACETrawlEvent
import eventseldlg
#import interactioncheckdlg

class startMACETrawlEvent():

    def __init__(self, parent):

#        if not parent.testing:
#            #  create an instance of the whale/bird interaction dialog and insert pictures
#            intDlg = interactioncheckdlg.InteractionCheckDlg(self)
#            pic = QImage()
#            if pic.load(parent.settings[QString('ImageDir')] + '/backgrounds/mm.jpg'):
#                pic = pic.scaledToHeight(intDlg.pic1.height(), Qt.SmoothTransformation)
#                intDlg.pic1.setPixmap(QPixmap.fromImage(pic))
#            pic = QImage()
#            if pic.load(parent.settings[QString('ImageDir')] + '/backgrounds/es.jpg'):
#                pic = pic.scaledToHeight(intDlg.pic2.height(), Qt.SmoothTransformation)
#                intDlg.pic2.setPixmap(QPixmap.fromImage(pic))


        #  create an instance of the event selection dialog
        hlDialog = eventseldlg.EventSelDlg(parent)

        #  display the event select dialog
        if hlDialog.exec():

            #  set the initial mammal and bird interaction checks to No
            parent.mammalStatus='N'
            parent.birdStatus='N'

            #  check if a event number was selected - exit if not
            if hlDialog.activeEvent==None:
                return

            #  set the active event
            parent.activeEvent = hlDialog.activeEvent
            parent.reloaded = hlDialog.reloaded

            # 1-9-22 RHT: Disabled the old protected spp dialog since we added
            # a PS observation time prior to a trawl in the trawl event.

            #  if this is the first time we've run the event selection dialog
#            if not parent.testing:
#                #  display the interaction dialog.
#                if not hlDialog.reloaded:
#                    if intDlg.exec_():
#                        if intDlg.yesBtn1.isChecked():
#                            parent.mammalStatus='Y'
#                        if intDlg.yesBtn2.isChecked():
#                            parent.birdStatus='Y'
#                    if intDlg.returnFlag:
#                        return

            # create an instance of the trawl event dialog and display
            trawlEvent = MACETrawlEvent.MACETrawlEvent(parent)
            trawlEvent.exec()
