# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Cera
                                 A QGIS plugin
 Coastal Erosion Risk Assessment
                             -------------------
        begin                : 2016-06-21
        copyright            : (C) 2016 by Pedro Narra
        email                : pedronarra@ua.pt
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load Cera class from file Cera.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .cera import Cera
    return Cera(iface)
