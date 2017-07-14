# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CERA
                                 A QGIS plugin
 Coastal Erosion Risk Assessment
                              -------------------
        begin                : 2016-11-17
        git sha              : $Format:%H$
        copyright            : (C) 2016 by NEFEC
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFileInfo
from PyQt4.QtGui import QAction, QIcon, QFileDialog
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from qgis.core import *
from PyQt4.QtGui import QMessageBox
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from cera_dialog import CERADialog
import os


class CERA:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'CERA_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = CERADialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Coastal Assessment')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'CERA')
        self.toolbar.setObjectName(u'CERA')

        self.dlg.path.clear()
        self.dlg.browse.clicked.connect(self.select_output_file)

        self.dlg.execute.clicked.connect(self.executecc2005)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('CERA', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/CERA/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'CERA'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Coastal Assessment'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()

        # Load active layers
        self.loadlayersbox()

        # Run the dialog event loop
        #result = self.dlg.exec_()
        # See if OK was pressed
        #if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
        #    pass



    def loadlayersbox(self):
        layers = self.iface.legendInterface().layers()

        # Clear the QComboBoxes before loading layers
        self.dlg.shoreline.clear()
        self.dlg.topography.clear()
        self.dlg.geology.clear()
        self.dlg.geomorphology.clear()
        self.dlg.ground.clear()
        self.dlg.anthropogenic.clear()
        self.dlg.wave.clear()
        self.dlg.tide.clear()
        self.dlg.rates.clear()

        # Clear the QComboBoxes of the consequence layers:
        self.dlg.population.clear()
        self.dlg.economy.clear()
        self.dlg.ecology.clear()
        self.dlg.heritage.clear()

        # Load layers in the QComboBoxes
        for layer in layers:
            if layer.type() == QgsMapLayer.RasterLayer:
                self.dlg.shoreline.addItem(layer.name(), layer)
                self.dlg.topography.addItem(layer.name(), layer)
                self.dlg.geology.addItem(layer.name(), layer)
                self.dlg.geomorphology.addItem(layer.name(), layer)
                self.dlg.ground.addItem(layer.name(), layer)
                self.dlg.anthropogenic.addItem(layer.name(), layer)
                self.dlg.wave.addItem(layer.name(), layer)
                self.dlg.tide.addItem(layer.name(), layer)
                self.dlg.rates.addItem(layer.name(), layer)
                self.dlg.population.addItem(layer.name(), layer)
                self.dlg.economy.addItem(layer.name(), layer)
                self.dlg.ecology.addItem(layer.name(), layer)
                self.dlg.heritage.addItem(layer.name(), layer)

    def select_output_file(self):
        filename = QFileDialog.getSaveFileName(self.dlg, "Select output file ","", '*.tif')
        self.dlg.path.setText(filename)

    def executecc2005(self):

        filename = self.dlg.path.text()
        print filename

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
            QMessageBox.warning(None, 'Done', 'Coastal Risk Assessment Complete!')

    def computeconsequences(self, consequencelayers, consequenceentries):
        filename = self.dlg.path.text()
        path = filename.replace(".tif","_consequence.tif")
        print 'O primeiro calculo tem o seguinte path:' + path
        formula = '(('+ consequenceentries[0].ref +' + '+ consequenceentries[3].ref +' + '+ consequenceentries[1].ref +' + '+ consequenceentries[2].ref +') / 4 >= '+ consequenceentries[0].ref +') * (('+ consequenceentries[0].ref +' + '+ consequenceentries[3].ref +' + '+ consequenceentries[1].ref +' + '+ consequenceentries[2].ref +') / 4) + (('+ consequenceentries[0].ref +' + '+ consequenceentries[3].ref +' + '+ consequenceentries[1].ref +' + '+ consequenceentries[2].ref +') / 4 < '+ consequenceentries[0].ref +') * '+ consequenceentries[0].ref
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
        newformula = '('+ entries[0].ref +' >= 0.5 AND '+ entries[0].ref +' < 1.5)*1+('+ entries[0].ref +' >= 1.5 AND '+ entries[0].ref +' < 2.5)*2+('+ entries[0].ref +' >= 2.5 AND '+ entries[0].ref +' < 3.5)*3+('+ entries[0].ref +' >= 3.5 AND '+ entries[0].ref +' < 4.5)*4+('+ entries[0].ref +' >= 4.5 AND '+ entries[0].ref +' < 5.5)*5'
		#newformula = '(' + entries[0].ref + ' < 1.5 AND ' + entries[0].ref + ' > 0) * 1 + (' + entries[0].ref + '>= 1.5 AND ' + entries[0].ref + ' < 2.5) * 2 + (' + entries[0].ref + ' >=2.5 AND ' + entries[0].ref + ' < 3.5) * 3 + (' + entries[0].ref + ' >=3.5 AND ' + entries[0].ref + ' < 4.5) * 4 + (' + entries[0].ref + ' >=4.5) * 5' # FALTA EDITAR A FORMULA
        print newformula
        #newpath = str(os.path.expanduser("~")) + '\Consequences.tif'
        newpath = filename.replace(".tif","_consequence_rounded.tif")
        print 'O segundo calculo tem o seguinte path:' + newpath
        
        newcalc = QgsRasterCalculator(newformula,
                                   newpath,
                                   'GTiff',
                                   extent,
                                   width,
                                   height,
                                   entries)
        newcalc.processCalculation()
        result = QgsRasterLayer(newpath,'Consequencias')
        if result.isValid():
            return result
        else:
            QMessageBox.warning(None, 'Coastal Risk Assessment', 'The output layer is not valid!')

    def computerisk(self, risklayers, riskentries):
        filename = self.dlg.path.text()
        path = filename.replace(".tif","_pre_result.tif")
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
        filename = self.dlg.path.text()
        path = filename.replace(".tif","_risk.tif")
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
        filename = self.dlg.path.text()
        path = filename.replace(".tif","_vulnerability.tif")
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
        sh100 = self.dlg.shoreline100.value()
        tp100 = self.dlg.topography100.value()
        gl100 = self.dlg.geology100.value()
        gm100 = self.dlg.geomorphology100.value()
        gr100 = self.dlg.ground100.value()
        ap100 = self.dlg.anthropogenic100.value()
        wv100 = self.dlg.wave100.value()
        td100 = self.dlg.tide100.value()
        rt100 = self.dlg.rates100.value()

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
        sh5000 = self.dlg.shoreline5000.value()
        tp5000 = self.dlg.topography5000.value()
        gl5000 = self.dlg.geology5000.value()
        gm5000 = self.dlg.geomorphology5000.value()
        gr5000 = self.dlg.ground5000.value()
        ap5000 = self.dlg.anthropogenic5000.value()
        wv5000 = self.dlg.wave5000.value()
        td5000 = self.dlg.tide5000.value()
        rt5000 = self.dlg.rates5000.value()

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
        shoreline = self.getlayerbyname(self.dlg.shoreline.currentText())
        topography = self.getlayerbyname(self.dlg.topography.currentText())
        geology = self.getlayerbyname(self.dlg.geology.currentText())
        geomorphology = self.getlayerbyname(self.dlg.geomorphology.currentText())
        ground = self.getlayerbyname(self.dlg.ground.currentText())
        anthropogenic = self.getlayerbyname(self.dlg.anthropogenic.currentText())
        wave = self.getlayerbyname(self.dlg.wave.currentText())
        tide = self.getlayerbyname(self.dlg.tide.currentText())
        rates = self.getlayerbyname(self.dlg.rates.currentText())
        layers = [shoreline, topography, geology, geomorphology, ground, anthropogenic, wave, tide, rates]
        return layers

    def loadconsequencelayers(self):
        population = self.getlayerbyname(self.dlg.population.currentText())
        economy = self.getlayerbyname(self.dlg.economy.currentText())
        ecology = self.getlayerbyname(self.dlg.ecology.currentText())
        heritage = self.getlayerbyname(self.dlg.heritage.currentText())
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
        filename = self.dlg.path.text()
        path = filename.replace(".tif","_distance_to_shoreline.tif")
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
