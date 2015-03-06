#   Copyright (C) 2015 Kevin S. Graer
#
#
# This file is part of PseudoTV Lite.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Lite.  If not, see <http://www.gnu.org/licenses/>.
        
    
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import os, sys, time, fileinput, re
import urllib, urllib2

from resources.lib.Globals import *


def showText(heading, text):
    log("showText")
    id = 10147
    xbmc.executebuiltin('ActivateWindow(%d)' % id)
    xbmc.sleep(100)
    win = xbmcgui.Window(id)
    retry = 50
    while (retry > 0):
        try:
            xbmc.sleep(10)
            retry -= 1
            win.getControl(1).setLabel(heading)
            win.getControl(5).setText(text)
            return
        except:
            pass
            
            
def showChangelog(addonID=None):
    log("showChangelog")
    try:
        if addonID:
            ADDON = xbmcaddon.Addon(addonID)
        else: 
            ADDON = xbmcaddon.Addon(ADDONID)
        f = open(ADDON.getAddonInfo('changelog'))
        text  = f.read()
        title = "Changelog - PseudoTV Lite"
        showText(title, text)
    except:
        pass

if sys.argv[1] == '-showChangelog':
    showChangelog(ADDON_ID)
