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
    :module:: HistogramPlot

    :synopsis: HistogramPlot is used by the Length module. It
               implements a QGraphicsScene displaying a histogram
               plot with length on the X axis and n_fish on the Y.

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assesment and Conservation Engineering Group (MACE)
|
| Author:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
| Maintained by:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
|       Mike Levine   <mike.levine@noaa.gov>
|       Nathan Lauffenburger   <nathan.lauffenburger@noaa.gov>
        Melina Shak <melina.shak@noaa.gov>
"""

from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt6.QtGui import QFont, QPen, QBrush
from PyQt6.QtWidgets import QGraphicsScene

class HistogramPlot(QGraphicsScene):
    """ HistogramPloth is a subclass of QGraphicsScene and draws a
    length frequency histogram of fish by sex.
    """
    def __init__(self, parent=None):
        super(HistogramPlot, self).__init__(parent)

        self.mLengthBars=[]
        self.fLengthBars=[]
        self.uLengthBars=[]

        # add frame

        self.addLine(QLineF(0, 0, 80, 0))
        self.addLine(QLineF(0, 1, 0, -20))
        self.scale=1.
        font=QFont('helvetica', 2, -1, False)
        # ticks
        for i in range(8):
            self.addLine(QLineF(i*10, 0, i*10, 1))
            t=self.addText(str(i*10), font)
            t.setPos(QPointF(i*10-6, 0))

    def rescale(self, scale):
        self.scale=scale
        for i in range(80):
            r=self.mLengthBars[i].rect()
            r.setHeight(r.height()*scale)
            self.mLengthBars[i].setRect(r)
            r=self.uLengthBars[i].rect()
            r.setHeight(r.height()*scale)
            self.uLengthBars[i].setRect(r)
            r=self.fLengthBars[i].rect()
            r.setHeight(r.height()*scale)
            self.fLengthBars[i].setRect(r)



    def clearPlot(self):
        for x in self.uLengthBars:
            self.removeItem(x)
        for x in self.fLengthBars:
            self.removeItem(x)
        for x in self.mLengthBars:
            self.removeItem(x)

        self.mLengthBars=[]
        self.fLengthBars=[]
        self.uLengthBars=[]
        linePen=QPen(Qt.GlobalColor.black, 0)
        ubrush=QBrush(Qt.GlobalColor.gray, Qt.BrushStyle.SolidPattern)
        mbrush=QBrush(Qt.GlobalColor.white, Qt.BrushStyle.SolidPattern)
        fbrush=QBrush(Qt.GlobalColor.black, Qt.BrushStyle.SolidPattern)
        barsize=1
        for i in range(80):
            self.uLengthBars.append(self.addRect(QRectF(i, 0, barsize, 0), linePen, ubrush))
            self.fLengthBars.append(self.addRect(QRectF(i, 0, barsize,0), linePen, fbrush))
            self.mLengthBars.append(self.addRect(QRectF(i, 0, barsize,0), linePen, mbrush))


    def update(self, length, sex):
        """
        Called periodically by a timer to update the count.
        """

        if sex=='Male':
            r=self.mLengthBars[length].rect()
            r.setHeight(r.height()-self.scale)
            self.mLengthBars[length].setRect(r)
            r=self.fLengthBars[length].rect()
            r.setHeight(r.height()-self.scale)
            self.fLengthBars[length].setRect(r)
            r=self.uLengthBars[length].rect()
            r.setHeight(r.height()-self.scale)
            self.uLengthBars[length].setRect(r)
        elif sex=='Female':
            r=self.fLengthBars[length].rect()
            r.setHeight(r.height()-self.scale)
            self.fLengthBars[length].setRect(r)
            r=self.uLengthBars[length].rect()
            r.setHeight(r.height()-self.scale)
            self.uLengthBars[length].setRect(r)
        else:
            r=self.uLengthBars[length].rect()
            r.setHeight(r.height()-self.scale)
            self.uLengthBars[length].setRect(r)



