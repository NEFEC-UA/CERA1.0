# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CeraDialog
                                 A QGIS plugin
 Coastal Erosion Risk Assessment
                             -------------------
        begin                : 2016-06-21
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Pedro Narra
        email                : pedronarra@ua.pt
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, uic
from PyQt4.QtGui import QMessageBox
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from qgis.core import *
import processing

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'cera_dialog_base.ui'))


class CeraDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(CeraDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.execute.clicked.connect(self.executecc2005)

    def executecc2005(self):
        [total100, rates100] = self.checkrates100() # load selected rates at 100 meters
        [total5000, rates5000] = self.checkrates5000() # load selected rates at 5000 meters
        if rates100 is None: # error if the sum is not equal to 1
            QMessageBox.warning(None, 'Coastal Risk Assessment', 'The sum of the rates at 100 m is not equal to 1. Current value is ' + str(total100))
        elif rates5000 is None: # error if the sum is not equal to 1
            QMessageBox.warning(None, 'Coastal Risk Assessment', 'The sum of the rates at 5000 m is not equal to 1. Current value is ' + str(total5000))
        else: # execute the calculations
            layers = self.loadlayers()
            entries = self.defineentries(layers)

            consequencelayers = self.loadconsequencelayers()
            consequenceentries = self.defineentries(consequencelayers)

            distancetoshoreline = self.createdistancemap(layers, entries) #create map of distance to shoreline
            entry_distancetoshoreline = self.defineentry(distancetoshoreline) #define entry for raster calculator

            layers.append(distancetoshoreline)
            entries.append(entry_distancetoshoreline)

            result = self.calculator(layers, rates100, rates5000, entries)
            #QgsMapLayerRegistry.instance().addMapLayer(result)

            rounded_result = self.roundresult(result)
            QgsMapLayerRegistry.instance().addMapLayer(rounded_result)

            print 'Calculo das consequencias'

            consequencias = self.computeconsequences(consequencelayers, consequenceentries)
            QgsMapLayerRegistry.instance().addMapLayer(consequencias)

            print 'Calculo de risco'

            risklayers = [rounded_result, consequencias]
            riskentries = self.defineentries(risklayers)
            risk = self.computerisk(risklayers, riskentries)
            QgsMapLayerRegistry.instance().addMapLayer(risk)

    def computeconsequences(self, consequencelayers, consequenceentries):
        path = str(os.path.expanduser("~")) + '\Consequences.tif'
        formula = '(((('+ consequenceentries[1].ref +' + '+ consequenceentries[0].ref +' + '+ consequenceentries[2].ref +' + '+ consequenceentries[3].ref +') / 4) >= '+ consequenceentries[0].ref +' AND (('+ consequenceentries[1].ref +' + '+ consequenceentries[0].ref +' + '+ consequenceentries[2].ref +' + '+ consequenceentries[3].ref +') / 4) >= 1) * (('+ consequenceentries[1].ref +' + '+ consequenceentries[0].ref +' + '+ consequenceentries[2].ref +' + '+ consequenceentries[3].ref +') / 4) + ((('+ consequenceentries[1].ref +' + '+ consequenceentries[0].ref +' + '+ consequenceentries[2].ref +' + '+ consequenceentries[3].ref +') / 4) < '+ consequenceentries[0].ref +' AND '+ consequenceentries[0].ref +' >= 1) * '+ consequenceentries[0].ref +')'
        print formula #try formula
        [extent, width, height] = self.resultextent(consequencelayers)

        calc = QgsRasterCalculator(formula,
                                   path,
                                   'GTiff',
                                   extent,
                                   width,
                                   height,
                                   consequenceentries)
        calc.processCalculation()
        consequences = QgsRasterLayer(path,'Consequencias')

        entries = []
        entry = self.defineentry(consequences)
        entries.append(entry)
        newformula = '(' + entries[0].ref + ' < 1.5 AND ' + entries[0].ref + ' > 0) * 1 + (' + entries[0].ref + '>= 1.5 AND ' + entries[0].ref + ' < 2.5) * 2 + (' + entries[0].ref + ' >=2.5 AND ' + entries[0].ref + ' < 3.5) * 3 + (' + entries[0].ref + ' >=3.5 AND ' + entries[0].ref + ' < 4.5) * 4 + (' + entries[0].ref + ' >=4.5) * 5' # FALTA EDITAR A FORMULA

        newpath = str(os.path.expanduser("~")) + '\Consequences.tif'

        newcalc = QgsRasterCalculator(newformula,
                                   newpath,
                                   'GTiff',
                                   extent,
                                   width,
                                   height,
                                   entries)
        newcalc.processCalculation()
        result = QgsRasterLayer(path,'Consequencias')
        if result.isValid():
            return result
        else:
            QMessageBox.warning(None, 'Coastal Risk Assessment', 'The output layer is not valid!')

    def computerisk(self, risklayers, riskentries):
        path = str(os.path.expanduser("~")) + '\Risk.tif'
        formula = '((( '+ riskentries[0].ref +' + '+ riskentries[1].ref +' )  < 4 AND  ( '+ riskentries[0].ref +' + '+ riskentries[1].ref +' )   >=  2 )  OR   (( '+ riskentries[0].ref +' + '+ riskentries[1].ref +' )  = 4 AND  ( '+ riskentries[0].ref +' = 3 OR '+ riskentries[1].ref +' = 3 ))) * 1 + (( '+ riskentries[0].ref +' = 2 AND '+ riskentries[1].ref +' = 2 ) OR ('+ riskentries[0].ref +' + '+ riskentries[1].ref +')  = 5) * 2 + (('+ riskentries[0].ref +' + '+ riskentries[1].ref +')  = 6) * 3 + (( '+ riskentries[0].ref +' = 4 AND '+ riskentries[1].ref +' = 4 ) OR ('+ riskentries[0].ref +' + '+ riskentries[1].ref +')  = 7) * 4 + ((( '+ riskentries[0].ref +' + '+ riskentries[1].ref +' )  > 8 AND  ( '+ riskentries[0].ref +' + '+ riskentries[1].ref +' )   <=  10 )  OR   (( '+ riskentries[0].ref +' + '+ riskentries[1].ref +' )  = 8 AND  ( '+ riskentries[0].ref +' = 5 OR '+ riskentries[1].ref +' = 5 ))) * 5'


        extent = risklayers[0].extent()
        width = risklayers[0].width()
        height = risklayers[0].height()

        calc = QgsRasterCalculator(formula,
                                   path,
                                   'GTiff',
                                   extent,
                                   width,
                                   height,
                                   riskentries)
        calc.processCalculation()
        risk = QgsRasterLayer(path,'Risco')

        if risk.isValid():
            return risk
        else:
            QMessageBox.warning(None, 'Coastal Risk Assessment', 'The output layer is not valid!')


    def roundresult(self, result):
        path = str(os.path.expanduser("~")) + '\Rounded_Vulnerability.tif'
        entries = []
        entry = self.defineentry(result)
        entries.append(entry)
        formula = '(' + entries[0].ref + ' < 1.5) * 1 + (' + entries[0].ref + '>= 1.5 AND ' + entries[0].ref + ' < 2.5) * 2 + (' + entries[0].ref + ' >=2.5 AND ' + entries[0].ref + ' < 3.5) * 3 + (' + entries[0].ref + ' >=3.5 AND ' + entries[0].ref + ' < 4.5) * 4 + (' + entries[0].ref + ' >=4.5) * 5' # FALTA EDITAR A FORMULA
        print formula
        print path
        extent = result.extent()
        width = result.width()
        height = result.height()
        print extent
        print width
        print height
        #[extent, width, height] = self.resultextent(layers) #

        calc = QgsRasterCalculator(formula,
                                   path,
                                   'GTiff',
                                   extent,
                                   width,
                                   height,
                                   entries)
        calc.processCalculation()
        result = QgsRasterLayer(path,'Vulnerabilidade')
        if result.isValid():
            return result
        else:
            QMessageBox.warning(None, 'Coastal Risk Assessment', 'The output layer is not valid!')

    def resultextent(self, layers):
        Xextent = layers[3].extent().xMaximum() - layers[3].extent().xMinimum()
        Yextent = layers[3].extent().yMaximum() - layers[3].extent().yMinimum()
        extent = layers[3].extent()
        width = 0
        height = 0
        for layer in layers:
            if Xextent > layer.extent().xMaximum() - layer.extent().xMinimum() and Yextent > layer.extent().yMaximum() - layer.extent().yMinimum():
                Xextent = layer.extent().xMaximum() - layer.extent().xMinimum()
                Yextent = layer.extent().yMaximum() - layer.extent().yMinimum()
                extent = layer.extent()
                print layer.name()
            else:
                pass
            if width < layer.width():
                width = layer.width()
            else:
                pass
            if height < layer.height():
                height = layer.height()
            else:
                pass
        print "Dados usados:"
        print extent
        print width
        print height
        return extent, width, height

    def calculator(self, layers, rates100, rates5000, entries):
        path = str(os.path.expanduser("~")) + '\Vulnerability.tif'
        formula = self.designformula(rates100, rates5000, entries)

        [extent, width, height] = self.resultextent(layers)

        calc = QgsRasterCalculator(formula,
                                   path,
                                   'GTiff',
                                   extent,
                                   width,
                                   height,
                                   entries)
        calc.processCalculation()
        result = QgsRasterLayer(path,'Vulnerabilidade')
        if result.isValid():
            return result
        else:
            QMessageBox.warning(None, 'Coastal Risk Assessment', 'The output layer is not valid!')

    def designformula(self, rates100, rates5000, entries):

        r = []
        for n in range(1,10):
            f100 = str(rates100[n]) + ' * ' + str(entries[n].ref)
            r.append(f100)
        formula100 = '(' + str(entries[0].ref) + ' < 100) * (' + r[0] + ' + ' + r[1] + ' + ' + r[2] + ' + ' + r[3] + ' + ' + r[4] + ' + ' + r[5] + ' + ' + r[6] + ' + ' + r[7] + ' + ' + r[8] + ' )'

        r = []
        for n in range(1,10):
            f100to5000 = '( ' + str(rates100[n]) + ' + (' + str(rates5000[n]) + ' - ' + str(rates100[n]) + ') * (' + str(entries[0].ref) + ' - 100) / (5000 - 100)) *' + str(entries[n].ref)
            r.append(f100to5000)
        formula100to5000 = '(' + str(entries[0].ref) + '  >= 100  AND ' + str(entries[0].ref) + '  <= 5000) * ( ' + r[0] + ' + ' + r[1] + ' + ' + r[2] + ' + ' + r[3] + ' + ' + r[4] + ' + ' + r[5] + ' + ' + r[6] + ' + ' + r[7] + ' + ' + r[8] + ' )'

        r = []
        for n in range(1,10):
            f5000 = str(rates5000[n]) + ' * ' + str(entries[n].ref)
            r.append(f5000)
        formula5000 = '( ' + str(entries[0].ref) + ' > 5000) * ( ' + r[0] + ' + ' + r[1] + ' + ' + r[2] + ' + ' + r[3] + ' + ' + r[4] + ' + ' + r[5] + ' + ' + r[6] + ' + ' + r[7] + ' + ' + r[8] + ' )'

        formula = formula100 + ' + ' + formula100to5000 + ' + ' + formula5000

        return formula

    def checkrates100(self):
        sh100 = self.shoreline100.value()
        tp100 = self.topography100.value()
        gl100 = self.geology100.value()
        gm100 = self.geomorphology100.value()
        gr100 = self.ground100.value()
        ap100 = self.anthropogenic100.value()
        wv100 = self.wave100.value()
        td100 = self.tide100.value()
        rt100 = self.rates100.value()

        rates100 = (0, tp100, gl100, gm100, gr100, ap100, wv100, td100, rt100, sh100)

        total100 = 0
        for rate in rates100:
            total100 += rate

        if total100 > 0.9999999 and total100 < 1.0000001:
            return total100, rates100
        else:
            rates100 = None
            return total100, rates100

    def checkrates5000(self):
        sh5000 = self.shoreline5000.value()
        tp5000 = self.topography5000.value()
        gl5000 = self.geology5000.value()
        gm5000 = self.geomorphology5000.value()
        gr5000 = self.ground5000.value()
        ap5000 = self.anthropogenic5000.value()
        wv5000 = self.wave5000.value()
        td5000 = self.tide5000.value()
        rt5000 = self.rates5000.value()

        rates5000 = (0, tp5000, gl5000, gm5000, gr5000, ap5000, wv5000, td5000, rt5000, sh5000)

        total5000 = 0
        for rate in rates5000:
            total5000 += rate

        if total5000 > 0.9999999 and total5000 < 1.0000001:
            return total5000, rates5000
        else:
            rates5000 = None
            return total5000, rates5000

    def loadlayers(self):
        shoreline = self.getlayerbyname(self.shoreline.currentText())
        topography = self.getlayerbyname(self.topography.currentText())
        geology = self.getlayerbyname(self.geology.currentText())
        geomorphology = self.getlayerbyname(self.geomorphology.currentText())
        ground = self.getlayerbyname(self.ground.currentText())
        anthropogenic = self.getlayerbyname(self.anthropogenic.currentText())
        wave = self.getlayerbyname(self.wave.currentText())
        tide = self.getlayerbyname(self.tide.currentText())
        rates = self.getlayerbyname(self.rates.currentText())
        layers = [shoreline, topography, geology, geomorphology, ground, anthropogenic, wave, tide, rates]
        return layers

    def loadconsequencelayers(self):
        population = self.getlayerbyname(self.population.currentText())
        economy = self.getlayerbyname(self.economy.currentText())
        ecology = self.getlayerbyname(self.ecology.currentText())
        heritage = self.getlayerbyname(self.heritage.currentText())
        consequencelayers = [population, economy, ecology, heritage]
        return consequencelayers

    def defineentry(self, layer):
        a = QgsRasterCalculatorEntry()
        a.ref = str(layer.name()) + '@1'
        a.raster = layer
        a.bandNumber = 1
        return a

    def defineentries(self, layers):
        entries = []
        for layer in layers:
            entry = self.defineentry(layer)
            entries.append(entry)
        return entries

    def getlayerbyname(self, layerName):
        layerMap = QgsMapLayerRegistry.instance().mapLayers()
        for name, layer in layerMap.iteritems():
            if layer.type() == QgsMapLayer.RasterLayer and layer.name() == layerName:
                if layer.isValid():
                    return layer
                else:
                    return None

    def createdistancemap(self, layers, entries):
        path = str(os.path.expanduser("~")) + '\DistancetoShoreline.tif'
        formula = '(' + entries[0].ref + ' > 1000) * 1 + (' + entries[0].ref + ' > 500 AND ' + entries[0].ref + ' <= 1000) * 2 + (' + entries[0].ref + ' > 300 AND ' + entries[0].ref + ' <= 500) * 3 +  (' + entries[0].ref + ' > 150 AND ' + entries[0].ref + ' <= 300) * 4 + (' + entries[0].ref + ' <= 150) * 5'
        calc = QgsRasterCalculator(formula,
                                   path,
                                   'GTiff',
                                   layers[0].extent(),
                                   layers[0].width(),
                                   layers[0].height(),
                                   entries)
        calc.processCalculation()
        result = QgsRasterLayer(path,'distancetoshoreline')
        if result.isValid():
            return result
        else:
            QMessageBox.warning(None, 'Coastal Risk Assessment', 'The output layer is not valid!')
