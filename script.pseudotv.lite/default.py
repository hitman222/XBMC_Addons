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
    
    
import os, sys, re, shutil, threading
import xbmc, xbmcgui, xbmcaddon, xbmcvfs

from resources.lib.ga import *
from resources.lib.Globals import *
from resources.lib.FileAccess import *
from resources.lib.utils import *

# Script constants
__scriptname__ = "PseudoTV Lite"
__author__     = "Lunatixz, Jason102"
__url__        = "https://github.com/Lunatixz/script.pseudotv.lite"
__settings__   = xbmcaddon.Addon(id='script.pseudotv.lite')
__cwd__        = __settings__.getAddonInfo('path')
__version__    = __settings__.getAddonInfo('version')
__language__   = __settings__.getLocalizedString
       
try:
    import buggalo
    buggalo.SUBMIT_URL = 'http://pseudotvlive.com/buggalo-web/submit.php'
except:
    pass

def PseudoTV():
    import resources.lib.Overlay as Overlay
    xbmcgui.Window(10000).setProperty("PseudoTVRunning", "True")

    try:
        MyOverlayWindow = Overlay.TVOverlay("script.pseudotv.live.TVOverlay.xml", __cwd__, Skin_Select)
    except Exception: 
        buggalo.addExtraData("Skin_Select = ", str(Skin_Select))
        buggalo.onExceptionRaised()
        Error('PseudoTV Lite','Error loading "' + Skin_Select + '" skin!','Verify selected skin in settings') 
        return
        
    for curthread in threading.enumerate():
        try:
            log("Active Thread: " + str(curthread.name), xbmc.LOGERROR)
            if curthread.name != "MainThread":
                try:
                    curthread.join()      
                except: 
                    pass
                log("Joined " + curthread.name)               
        except: 
            pass
            
    del MyOverlayWindow
    xbmcgui.Window(10000).setProperty("PseudoTVRunning", "False")

    
# Adapting a solution from ronie (http://forum.xbmc.org/showthread.php?t=97353)
if xbmcgui.Window(10000).getProperty("PseudoTVRunning") != "True":    
    try:
        PTVL_Version = REAL_SETTINGS.getSetting("PTVL_Version")
    except:
        REAL_SETTINGS.setSetting("PTVL_Version", __version__)
        PTVL_Version = REAL_SETTINGS.getSetting("PTVL_Version") 
    
    if PTVL_Version != __version__:
        ClearPlaylists()
        REAL_SETTINGS.setSetting('ForceChannelReset', 'true')
        REAL_SETTINGS.setSetting("PTVL_Version", __version__)

        # Auto VideoWindow Patch.
        VideoWindow()
        
        #call showChangeLog like this to workaround bug in openElec, *Thanks spoyser
        xbmc.executebuiltin("RunScript("+__cwd__+"/utilities.py,-showChangelog)")
        
        if dlg.yesno("PseudoTV Lite", "System Reboot recommend after update, Exit XBMC?"):
            xbmc.executebuiltin( "XBMC.AlarmClock(shutdowntimer,XBMC.Quit(),%d,true)" % ( 0.5, ) )         
    else:
        #Check if Outdated/Install Repo
        VersionCompare()
        
        # #Check Messaging Service todo
        # Announcement()

        # Auto VideoWindow Patch.
        VideoWindow()
        
        #Back/Restore Settings2
        settingsFile = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'settings2.xml'))
        nsettingsFile = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'settings2.bak.xml'))
        atsettingsFile = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'settings2.pretune.xml'))
        
        try:
            Normal_Shutdown = REAL_SETTINGS.getSetting('Normal_Shutdown') == "true"
        except:
            REAL_SETTINGS.setSetting('Normal_Shutdown', "true")
            Normal_Shutdown = REAL_SETTINGS.getSetting('Normal_Shutdown') == "true"
                
        if REAL_SETTINGS.getSetting("ATRestore") == "true" and REAL_SETTINGS.getSetting("Warning2") == "true":
            log('Setting2 ATRestore onInit') 
            if getSize(atsettingsFile) > 100:
                REAL_SETTINGS.setSetting("ATRestore","false")
                REAL_SETTINGS.setSetting("Warning2","false")
                REAL_SETTINGS.setSetting('ForceChannelReset', 'true')
                Restore(atsettingsFile, settingsFile)   
        elif Normal_Shutdown == False:
            log('Setting2 Restore onInit') 
            if getSize(settingsFile) < 100 and getSize(nsettingsFile) > 100:
                Restore(nsettingsFile, settingsFile)
        else:
            log('Setting2 Backup onInit') 
            if getSize(settingsFile) > 100:
                Backup(settingsFile, nsettingsFile)

        REAL_SETTINGS.setSetting("ArtService_onInit","false")
        REAL_SETTINGS.setSetting("ArtService_Running","false")
        #Start PseudoTV
        PseudoTV()
else:
    log('script.pseudotv.lite - Already running, exiting', xbmc.LOGERROR)
    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Lite", "Already running, Please Wait...", 1000, THUMB) )