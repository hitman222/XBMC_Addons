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
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, datetime, random
import threading
import sys, re
import random, traceback
import urllib, urllib2, urlparse
import socket

from ChannelList import *
from Globals import *
from FileAccess import FileAccess
from xml.etree import ElementTree as ET
from urllib import unquote, quote
from utils import *

try:
    import buggalo
    buggalo.SUBMIT_URL = 'http://pseudotvlive.com/buggalo-web/submit.php'
except:
    pass
    
socket.setdefaulttimeout(30)

class Artdownloader:

    def __init__(self):
        self.chanlist = ChannelList()


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('Artdownloader: ' + msg, level)

    
    def logDebug(self, msg, level = xbmc.LOGDEBUG):
        if DEBUG == 'true':
            log('Artdownloader: ' + msg, level)
    
    
    #Find ChannelBug, then Convert if enabled.
    def FindBug(self, chtype, chname, mediapath):
        self.log("FindBug")
        setImage = ''
        BugName = (chname[0:18] + '.png')
        DefaultBug = os.path.join(IMAGES_LOC,'Default.png')
        BugFLE = xbmc.translatePath(os.path.join(LOGO_LOC,BugName))
        if not FileAccess.exists(BugFLE):
            BugFLE = DefaultBug
        return BugFLE
        

    def FindLogo(self, chtype, chname, mediapath):
        self.log("FindLogo")
        found = False
        setImage = ''
        LogoName = (chname[0:18] + '.png')
        LogoFolder = os.path.join(LOGO_LOC,LogoName)
        self.logoParser = lsHTMLParser()
        if FileAccess.exists(LogoFolder):
            setImage = LogoFolder
        else:
            setImage = 'NA.png'
        return setImage
     
     
    def FindArtwork(self, type, chtype, chname, id, dbid, mpath, arttypeEXT):
        self.log("FindArtwork, type = " + type + ' :chtype = ' + str(chtype) + ' :chname = ' + chname + ' :id = ' + str(id) + ' :dbid = ' + str(dbid) + ' :mpath = ' + mpath + ' :arttypeEXT = ' + arttypeEXT)
        setImage = ''
        CacheArt = False
        DefaultArt = False
        arttype = arttypeEXT.split(".")[0]
        arttypeEXT_fallback = arttypeEXT.replace('landscape','fanart').replace('clearart','logo').replace('character','logo').replace('folder','poster')
        arttype_fallback = arttypeEXT_fallback.split(".")[0]
        
        if int(chtype) <= 7:
            self.logDebug('FindArtwork, Infolder Artwork')
            smpath = mpath.rsplit('/',2)[0] #Path Above mpath ie Series folder
            artSeries = xbmc.translatePath(os.path.join(smpath, arttypeEXT))
            artSeason = xbmc.translatePath(os.path.join(mpath, arttypeEXT))
            artSeries_fallback = xbmc.translatePath(os.path.join(smpath, arttypeEXT_fallback))
            artSeason_fallback = xbmc.translatePath(os.path.join(mpath, arttypeEXT_fallback))

            if FileAccess.exists(artSeries): 
                return artSeries
            elif FileAccess.exists(artSeason):
                return artSeason
            elif FileAccess.exists(artSeries_fallback): 
                return artSeries_fallback
            elif FileAccess.exists(artSeason_fallback):
                return artSeason_fallback
        else:
            return self.SetDefaultArt(chname, mpath, arttypeEXT)
               
    
    def SetDefaultArt(self, chname, mpath, arttypeEXT):
        self.log('SetDefaultArt')
        setImage = ''
        arttype = arttypeEXT.split(".")[0]
        MediaImage = os.path.join(MEDIA_LOC, (arttype + '.png'))
        StockImage = os.path.join(IMAGES_LOC, (arttype + '.png'))
        ChannelLogo = os.path.join(LOGO_LOC,chname[0:18] + '.png')
        
        if FileAccess.exists(ChannelLogo):
            self.logDebug('SetDefaultArt, Channel Logo')
            return ChannelLogo
        elif mpath[0:6] == 'plugin':
            self.logDebug('SetDefaultArt, Plugin Icon')
            icon = 'special://home/addons/'+(mpath.replace('plugin://',''))+ '/icon.png'
            return icon
        elif FileAccess.exists(MediaImage):
            self.logDebug('SetDefaultArt, Media Image')
            return MediaImage
        elif FileAccess.exists(StockImage):
            self.logDebug('SetDefaultArt, Stock Image')
            return StockImage
        else:
            self.logDebug('SetDefaultArt, THUMB')
            return THUMB    