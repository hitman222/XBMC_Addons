#   Copyright (C) 2015 Jason Anderson, Kevin S. Graer
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

import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import subprocess, os, sys, re
import time, datetime, threading, _strptime, calendar
import httplib, urllib, urllib2, socket, json
import base64, shutil, random, errno
import Globals

from urllib import unquote
from urllib import urlopen
from xml.etree import ElementTree as ET
from xml.dom.minidom import parse, parseString
from subprocess import Popen, PIPE, STDOUT
from Playlist import Playlist
from Globals import *
from Channel import Channel
from VideoParser import VideoParser
from FileAccess import FileAccess
from urllib2 import urlopen
from urllib2 import HTTPError, URLError
from datetime import date
from utils import *
from datetime import timedelta, timedelta

socket.setdefaulttimeout(30)

try:
    import buggalo
    buggalo.SUBMIT_URL = 'http://pseudotvlive.com/buggalo-web/submit.php'
except:
    pass
    
class ChannelList:
    def __init__(self):
        self.networkList = []
        self.studioList = []
        self.mixedGenreList = []
        self.showGenreList = []
        self.movieGenreList = []
        self.musicGenreList = []
        self.FavouritesPathList = []
        self.FavouritesNameList = []
        self.showList = []
        self.channels = []
        self.cached_json_detailed_TV = []
        self.cached_json_detailed_Movie = []
        self.cached_json_detailed_xmltvChannels_pvr = []
        self.videoParser = VideoParser()
        self.autoplaynextitem = False
        self.sleepTime = 0
        self.threadPaused = False
        self.runningActionChannel = 0
        self.runningActionId = 0
        self.enteredChannelCount = 0
        self.background = True
        self.seasonal = False
        random.seed() 

        
    def readConfig(self):
        self.ResetChanLST = list(REAL_SETTINGS.getSetting('ResetChanLST'))
        self.log('Channel Reset List is ' + str(self.ResetChanLST))
        self.channelResetSetting = int(REAL_SETTINGS.getSetting("ChannelResetSetting"))
        self.log('Channel Reset Setting is ' + str(self.channelResetSetting))
        self.forceReset = REAL_SETTINGS.getSetting('ForceChannelReset') == "true"
        self.log('Force Reset is ' + str(self.forceReset))
        self.updateDialog = xbmcgui.DialogProgress()
        self.startMode = int(REAL_SETTINGS.getSetting("StartMode"))
        self.log('Start Mode is ' + str(self.startMode))
        self.backgroundUpdating = int(REAL_SETTINGS.getSetting("ThreadMode"))
        
        try:
            self.limit = MEDIA_LIMIT[int(REAL_SETTINGS.getSetting('MEDIA_LIMIT'))]
        except:
            self.log('Channel Media Limit Failed!')
            self.limit = 25
        self.log('Channel Media Limit is ' + str(self.limit))
        self.findMaxChannels()
        
        if self.forceReset:
            REAL_SETTINGS.setSetting('ForceChannelReset', 'false')
            REAL_SETTINGS.setSetting('StartupMessage', 'false')    
            self.forceReset = False

        try:
            self.lastResetTime = int(ADDON_SETTINGS.getSetting("LastResetTime"))
        except Exception,e:
            self.lastResetTime = 0

        try:
            self.lastExitTime = int(ADDON_SETTINGS.getSetting("LastExitTime"))
        except Exception,e:
            self.lastExitTime = int(time.time())
            
            
    def setupList(self):
        self.log("setupList")
        self.readConfig()
        self.updateDialog.create("PseudoTV Lite", "Updating channel list")
        self.updateDialog.update(0, "Updating channel list")
        self.updateDialogProgress = 0
        foundvalid = False
        makenewlists = False
        self.background = False
        
        if self.backgroundUpdating > 0 and self.myOverlay.isMaster == True:
            makenewlists = True
            
        # Go through all channels, create their arrays, and setup the new playlist
        for i in range(self.maxChannels):
            self.updateDialogProgress = i * 100 // self.enteredChannelCount
            self.updateDialog.update(self.updateDialogProgress, "Loading channel " + str(i + 1), "waiting for file lock", "")
            self.channels.append(Channel())
            
            # If the user pressed cancel, stop everything and exit
            if self.updateDialog.iscanceled():
                self.log('Update channels cancelled')
                self.updateDialog.close()
                return None
                
            self.setupChannel(i + 1, self.background, makenewlists, False)
            
            if self.channels[i].isValid:
                foundvalid = True

        if makenewlists == True:
            REAL_SETTINGS.setSetting('ForceChannelReset', 'false')

        if foundvalid == False and makenewlists == False:
            for i in range(self.maxChannels):
                self.updateDialogProgress = i * 100 // self.enteredChannelCount
                self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(i + 1), "waiting for file lock", '')
                self.setupChannel(i + 1, self.background, True, False)

                if self.channels[i].isValid:
                    foundvalid = True
                    break

        self.updateDialog.update(100, "Update complete")
        self.updateDialog.close()
        return self.channels 

        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('ChannelList: ' + msg, level)

    
    def logDebug(self, msg, level = xbmc.LOGDEBUG):
        if DEBUG == 'true':
            log('ChannelList: ' + msg, level)
            
            
    # Determine the maximum number of channels by opening consecutive
    # playlists until we don't find one
    def findMaxChannels(self):
        self.log('findMaxChannels')
        self.maxChannels = 0
        self.enteredChannelCount = 0

        for i in range(999):
            chtype = 9999
            chsetting1 = ''
            chsetting2 = ''
            chsetting3 = ''
            chsetting4 = ''

            try:
                chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_type'))
                chsetting1 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_1')
                chsetting2 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_2')
                chsetting3 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_3')
                chsetting4 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_4')
            except Exception,e:
                pass

            if chtype == 0:
                if FileAccess.exists(xbmc.translatePath(chsetting1)):
                    self.maxChannels = i + 1
                    self.enteredChannelCount += 1
            elif chtype <= 20:
                if len(chsetting1) > 0:
                    self.maxChannels = i + 1
                    self.enteredChannelCount += 1
                    
            if self.forceReset and (chtype != 9999):
                ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_changed', "True")

        self.log('findMaxChannels return ' + str(self.maxChannels))

    
    # Code for sending JSON through http adapted from code by sffjunkie (forum.xbmc.org/showthread.php?t=92196)
    def sendJSON(self, command):
        self.log('sendJSON')
        data = ''
            
        try:
            data = xbmc.executeJSONRPC(uni(command))
        except UnicodeEncodeError:
            data = xbmc.executeJSONRPC(ascii(command))

        return uni(data)
        
     
    def setupChannel(self, channel, background = False, makenewlist = False, append = False):
        self.log('setupChannel ' + str(channel))
        returnval = False
        createlist = makenewlist
        chtype = 9999
        chsetting1 = ''
        chsetting2 = ''
        chsetting3 = ''
        chsetting4 = ''
        needsreset = False
        self.background = background
        self.settingChannel = channel

        try:
            chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_type'))
            chsetting1 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_1')
            chsetting2 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_2')
            chsetting3 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_3')
            chsetting4 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_4')
        except:
            pass

        while len(self.channels) < channel:
            self.channels.append(Channel())

        if chtype == 9999:
            self.channels[channel - 1].isValid = False
            return False

        # self.channels[channel - 1].type = chtype
        self.channels[channel - 1].isSetup = True
        self.channels[channel - 1].loadRules(channel)
        self.runActions(RULES_ACTION_START, channel, self.channels[channel - 1])

        try:
            needsreset = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_changed') == 'True'
            
            # force rebuild
            if chtype == 8 or chtype == 16:
                self.log("Force LiveTV rebuild")
                needsreset = True
                
            if needsreset:
                if chtype <= 7:
                    localTV.delete("%")
                self.channels[channel - 1].isSetup = False
        except:
            pass

        # If possible, use an existing playlist
        # Don't do this if we're appending an existing channel
        # Don't load if we need to reset anyway
        if FileAccess.exists(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') and append == False and needsreset == False:
            try:
                self.channels[channel - 1].totalTimePlayed = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_time', True))
                createlist = True

                if self.background == False:
                    self.updateDialog.update(self.updateDialogProgress, "Loading channel " + str(channel), "reading playlist", '')

                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == True:
                    self.channels[channel - 1].isValid = True
                    self.channels[channel - 1].fileName = CHANNELS_LOC + 'channel_' + str(channel) + '.m3u'
                    returnval = True

                    # If this channel has been watched for longer than it lasts, reset the channel
                    if self.channelResetSetting == 0 and self.channels[channel - 1].totalTimePlayed < self.channels[channel - 1].getTotalDuration():
                        createlist = False

                    if self.channelResetSetting > 0 and self.channelResetSetting < 4:
                        timedif = time.time() - self.lastResetTime

                        if self.channelResetSetting == 1 and timedif < (60 * 60 * 24):
                            createlist = False

                        if self.channelResetSetting == 2 and timedif < (60 * 60 * 24 * 7):
                            createlist = False

                        if self.channelResetSetting == 3 and timedif < (60 * 60 * 24 * 30):
                            createlist = False

                        if timedif < 0:
                            createlist = False

                    if self.channelResetSetting == 4:
                        createlist = False
            except:
                pass

        if createlist or needsreset:
            self.channels[channel - 1].isValid = False

            if makenewlist:
                try:
                    xbmcvfs.delete(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u')
                except Exception,e:
                    pass

                append = False

                if createlist:
                    ADDON_SETTINGS.setSetting('LastResetTime', str(int(time.time())))

        if append == False:
            if chtype == 6 and chsetting2 == str(MODE_ORDERAIRDATE):
                self.channels[channel - 1].mode = MODE_ORDERAIRDATE

            # if there is no start mode in the channel mode flags, set it to the default
            if self.channels[channel - 1].mode & MODE_STARTMODES == 0:
                if self.startMode == 0:
                    self.channels[channel - 1].mode |= MODE_RESUME
                elif self.startMode == 1:
                    self.channels[channel - 1].mode |= MODE_REALTIME
                elif self.startMode == 2:
                    self.channels[channel - 1].mode |= MODE_RANDOM

        if ((createlist or needsreset) and makenewlist) or append:
            if self.background == False:
                self.updateDialogProgress = (channel - 1) * 100 // self.enteredChannelCount
                self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "", '')

            if self.makeChannelList(channel, chtype, chsetting1, chsetting2, chsetting3, chsetting4, append) == True:
                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == True:
                    returnval = True
                    self.channels[channel - 1].fileName = CHANNELS_LOC + 'channel_' + str(channel) + '.m3u'
                    self.channels[channel - 1].isValid = True
                    
                    # Don't reset variables on an appending channel
                    if append == False:
                        self.channels[channel - 1].totalTimePlayed = 0
                        ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_time', '0')

                        if needsreset:
                            if channel not in self.ResetChanLST:
                                ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_changed', 'False')
                            REAL_SETTINGS.setSetting('ResetChanLST', '')
                            self.channels[channel - 1].isSetup = True
                    
        self.runActions(RULES_ACTION_BEFORE_CLEAR, channel, self.channels[channel - 1])

        # Don't clear history when appending channels
        if self.background == False and append == False and self.myOverlay.isMaster:
            self.updateDialogProgress = (channel - 1) * 100 // self.enteredChannelCount
            self.updateDialog.update(self.updateDialogProgress, "Loading channel " + str(channel), "clearing history", '')
            self.clearPlaylistHistory(channel)

        if append == False:
            self.runActions(RULES_ACTION_BEFORE_TIME, channel, self.channels[channel - 1])

            if self.channels[channel - 1].mode & MODE_ALWAYSPAUSE > 0:
                self.channels[channel - 1].isPaused = True

            if self.channels[channel - 1].mode & MODE_RANDOM > 0:
                self.channels[channel - 1].showTimeOffset = random.randint(0, self.channels[channel - 1].getTotalDuration())

            if self.channels[channel - 1].mode & MODE_REALTIME > 0:
                timedif = int(self.myOverlay.timeStarted) - self.lastExitTime
                self.channels[channel - 1].totalTimePlayed += timedif

            if self.channels[channel - 1].mode & MODE_RESUME > 0:
                self.channels[channel - 1].showTimeOffset = self.channels[channel - 1].totalTimePlayed
                self.channels[channel - 1].totalTimePlayed = 0

            while self.channels[channel - 1].showTimeOffset > self.channels[channel - 1].getCurrentDuration():
                self.channels[channel - 1].showTimeOffset -= self.channels[channel - 1].getCurrentDuration()
                self.channels[channel - 1].addShowPosition(1)

        self.channels[channel - 1].name = self.getChannelName(chtype, chsetting1)

        if ((createlist or needsreset) and makenewlist) and returnval:
            self.runActions(RULES_ACTION_FINAL_MADE, channel, self.channels[channel - 1])
        else:
            self.runActions(RULES_ACTION_FINAL_LOADED, channel, self.channels[channel - 1])
        
        return returnval

        
    def clearPlaylistHistory(self, channel):
        self.log("clearPlaylistHistory")

        if self.channels[channel - 1].isValid == False:
            self.log("channel not valid, ignoring")
            return

        # if we actually need to clear anything
        if self.channels[channel - 1].totalTimePlayed > (60 * 60 * 24 * 2):
            try:
                fle = FileAccess.open(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u', 'w')
            except:
                self.log("clearPlaylistHistory Unable to open the smart playlist", xbmc.LOGERROR)
                return

            flewrite = uni("#EXTM3U\n")
            tottime = 0
            timeremoved = 0

            for i in range(self.channels[channel - 1].Playlist.size()):
                tottime += self.channels[channel - 1].getItemDuration(i)

                if tottime > (self.channels[channel - 1].totalTimePlayed - (60 * 60 * 12)):
                    tmpstr = str(self.channels[channel - 1].getItemDuration(i)) + ','
                    tmpstr += self.channels[channel - 1].getItemTitle(i) + "//" + self.channels[channel - 1].getItemEpisodeTitle(i) + "//" + self.channels[channel - 1].getItemDescription(i) + "//" + self.channels[channel - 1].getItemgenre(i) + "//" + self.channels[channel - 1].getItemtimestamp(i) + "//" + self.channels[channel - 1].getItemLiveID(i)
                    tmpstr = uni(tmpstr[:2036])
                    tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                    tmpstr = uni(tmpstr) + uni('\n') + uni(self.channels[channel - 1].getItemFilename(i))
                    flewrite += uni("#EXTINF:") + uni(tmpstr) + uni("\n")
                else:
                    timeremoved = tottime

            fle.write(flewrite)
            fle.close()

            if timeremoved > 0:
                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == False:
                    self.channels[channel - 1].isValid = False
                else:
                    self.channels[channel - 1].totalTimePlayed -= timeremoved
                    # Write this now so anything sharing the playlists will get the proper info
                    ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_time', str(self.channels[channel - 1].totalTimePlayed))


    def getChannelName(self, chtype, setting1):
        self.log('getChannelName ' + str(chtype))
        
        if chtype <= 7 or chtype == 12:
            if len(setting1) == 0:
                return ''

        if chtype == 0:
            return self.getSmartPlaylistName(setting1)
        elif chtype == 1 or chtype == 2 or chtype == 5 or chtype == 6 or chtype == 12:
            return setting1
        elif chtype == 3:
            return setting1 + " TV"
        elif chtype == 4:
            return setting1 + " Movies"
        elif chtype == 12:
            return setting1 + " Music"
        elif chtype == 7:
            if setting1[-1] == '/' or setting1[-1] == '\\':
                return os.path.split(setting1[:-1])[1]
            else:
                return os.path.split(setting1)[1]
        elif chtype == 8:
            #setting1 = channel
            return ADDON_SETTINGS.getSetting("Channel_" + str(setting1) + "_opt_1")        
        return ''


    # Open the smart playlist and read the name out of it...this is the channel name
    def getSmartPlaylistName(self, fle):
        self.log('getSmartPlaylistName')
        fle = xbmc.translatePath(fle)

        try:
            xml = FileAccess.open(fle, "r")
        except:
            self.log("getSmartPlaylistName Unable to open the smart playlist " + fle, xbmc.LOGERROR)
            return ''

        try:
            dom = parse(xml)
        except:
            self.log('getSmartPlaylistName Problem parsing playlist ' + fle, xbmc.LOGERROR)
            xml.close()
            return ''

        xml.close()

        try:
            plname = dom.getElementsByTagName('name')
            self.log('getSmartPlaylistName return ' + plname[0].childNodes[0].nodeValue)
            return plname[0].childNodes[0].nodeValue
        except:
            self.log("Unable to get the playlist name.", xbmc.LOGERROR)
            return ''
    
    
    # Based on a smart playlist, create a normal playlist that can actually be used by us
    def makeChannelList(self, channel, chtype, setting1, setting2, setting3, setting4, append = False):
        self.log('makeChannelList, CHANNEL: ' + str(channel))
        fileListCHK = False
        israndom = False  
        reverseOrder = False
        fileList = []
        setting4 = setting4.replace('Default','0').replace('Random','1').replace('Reverse','2') 
        
        if setting4 == '0':
            #DEFAULT
            israndom = False  
            reverseOrder = False
        elif setting4 == '1':
            #RANDOM
            israndom = True
            reverseOrder = False
        elif setting4 == '2':
            #REVERSE ORDER
            israndom = False
            reverseOrder = True
        
        #Set Limit Local or Global
        if setting3 and chtype > 9 and len(setting3) > 0:
            limit = int(setting3)
            self.log("makeChannelList, Overriding Global Parse-limit to " + str(limit))
        else:
            #Set MediaLimit
            if chtype == 7 and self.limit == 0:
                limit = 1000
            elif chtype == 8:
                limit = 72
            elif chtype >= 10:
                if self.limit == 0 or self.limit > 200:
                    limit = 200
                elif self.limit < 25:
                    limit = 25
                else:
                    limit = self.limit
            else:
                limit = self.limit
            self.log("makeChannelList, Using Global Parse-limit " + str(limit))
        
        # Directory
        if chtype == 7:
            fileList = self.createDirectoryPlaylist(setting1, setting3, setting4, limit)     
            
        # LiveTV
        elif chtype == 8:
            self.log("Building LiveTV Channel, " + setting1 + " , " + setting2 + " , " + setting3)
            
            # HDHomeRun #
            if setting2[0:9] == 'hdhomerun' and REAL_SETTINGS.getSetting('HdhomerunMaster') == "true":
                #If you're using a HDHomeRun Dual and want Tuner 1 assign false. *Thanks Blazin912*
                self.log("Building LiveTV using tuner0")
                setting2 = re.sub(r'\d/tuner\d',"0/tuner0",setting2)
            elif setting2[0:9] == 'hdhomerun' and REAL_SETTINGS.getSetting('HdhomerunMaster') == "false":
                self.log("Building LiveTV using tuner1")
                setting2 = re.sub(r'\d/tuner\d',"1/tuner1",setting2) 
            # Validate Feed #
            fileListCHK = self.Valid_ok(setting2)
            if fileListCHK == True:
                # Validate XMLTV Data #
                xmltvValid = self.xmltv_ok(setting3)
                
                if xmltvValid == True:
                    fileList = self.buildLiveTVFileList(setting1, setting2, setting3, setting4, limit) 
            else:
                self.log('makeChannelList, CHANNEL: ' + str(channel) + ', CHTYPE: ' + str(chtype), 'fileListCHK invalid: ' + str(setting2))
                return
                
        # InternetTV  
        elif chtype == 9:
            self.log("Building InternetTV Channel, " + setting1 + " , " + setting2 + " , " + setting3)
            # Validate Feed #
            fileListCHK = self.Valid_ok(setting2)
            if fileListCHK == True:
                fileList = self.buildInternetTVFileList(setting1, setting2, setting3, setting4)
            else:
                self.log('makeChannelList, CHANNEL: ' + str(channel) + ', CHTYPE: ' + str(chtype), 'fileListCHK invalid: ' + str(setting2))
                return 

        # LocalTV
        else:
            if chtype == 0:
                if FileAccess.copy(setting1, MADE_CHAN_LOC + os.path.split(setting1)[1]) == False:
                    if FileAccess.exists(MADE_CHAN_LOC + os.path.split(setting1)[1]) == False:
                        self.log("Unable to copy or find playlist " + setting1)
                        return False

                fle = MADE_CHAN_LOC + os.path.split(setting1)[1]
            else:
                fle = self.makeTypePlaylist(chtype, setting1, setting2)
           
            if len(fle) == 0:
                self.log('Unable to locate the playlist for channel ' + str(channel), xbmc.LOGERROR)
                return False

            try:
                xml = FileAccess.open(fle, "r")
            except Exception,e:
                self.log("makeChannelList Unable to open the smart playlist " + fle, xbmc.LOGERROR)
                return False

            try:
                dom = parse(xml)
            except Exception,e:
                self.log('makeChannelList Problem parsing playlist ' + fle, xbmc.LOGERROR)
                xml.close()
                return False

            xml.close()

            if self.getSmartPlaylistType(dom) == 'mixed':
                fileList = self.buildMixedFileList(dom, channel, limit)

            elif self.getSmartPlaylistType(dom) == 'movies':
                fileList = self.buildFileList(fle, channel, limit)
            
            elif self.getSmartPlaylistType(dom) == 'episodes':
                fileList = self.buildFileList(fle, channel, limit)

            try:
                order = dom.getElementsByTagName('order')

                if order[0].childNodes[0].nodeValue.lower() == 'random':
                    israndom = True
            except Exception,e:
                pass

        try:
            if append == True:
                channelplaylist = FileAccess.open(CHANNELS_LOC + "channel_" + str(channel) + ".m3u", "r+")
                channelplaylist.seek(0, 2)
            else:
                channelplaylist = FileAccess.open(CHANNELS_LOC + "channel_" + str(channel) + ".m3u", "w")
        except Exception,e:
            self.log('Unable to open the cache file ' + CHANNELS_LOC + 'channel_' + str(channel) + '.m3u', xbmc.LOGERROR)
            return False

        if append == False:
            channelplaylist.write(uni("#EXTM3U\n"))
            #first queue m3u
            
        if fileList != None:  
            if len(fileList) == 0:
                self.log("Unable to get information about channel " + str(channel), xbmc.LOGERROR)
                channelplaylist.close()
                return False

        if israndom:
            random.shuffle(fileList)
            
        if reverseOrder:
            fileList.reverse()

        if len(fileList) > 16384:
            fileList = fileList[:16384]

        fileList = self.runActions(RULES_ACTION_LIST, channel, fileList)
        self.channels[channel - 1].isRandom = israndom

        if append:
            if len(fileList) + self.channels[channel - 1].Playlist.size() > 16384:
                fileList = fileList[:(16384 - self.channels[channel - 1].Playlist.size())]
        else:
            if len(fileList) > 16384:
                fileList = fileList[:16384]

        # Write each entry into the new playlist
        for string in fileList:
            channelplaylist.write(uni("#EXTINF:") + uni(string) + uni("\n"))
            
        channelplaylist.close()
        self.log('makeChannelList return')
        return True

        
    def makeTypePlaylist(self, chtype, setting1, setting2):
    
        if chtype == 1:
            if len(self.networkList) == 0:
                self.fillTVInfo()
            return self.createNetworkPlaylist(setting1)
            
        elif chtype == 2:
            if len(self.studioList) == 0:
                self.fillMovieInfo()
            return self.createStudioPlaylist(setting1)
            
        elif chtype == 3:
            if len(self.showGenreList) == 0:
                self.fillTVInfo()
            return self.createGenrePlaylist('episodes', chtype, setting1)
            
        elif chtype == 4:
            if len(self.movieGenreList) == 0:
                self.fillMovieInfo()
            return self.createGenrePlaylist('movies', chtype, setting1)
            
        elif chtype == 5:
            if len(self.mixedGenreList) == 0:
                if len(self.showGenreList) == 0:
                    self.fillTVInfo()

                if len(self.movieGenreList) == 0:
                    self.fillMovieInfo()

                self.mixedGenreList = self.makeMixedList(self.showGenreList, self.movieGenreList)
                self.mixedGenreList.sort(key=lambda x: x.lower())
            return self.createGenreMixedPlaylist(setting1)
            
        elif chtype == 6:
            if len(self.showList) == 0:
                self.fillTVInfo()
            return self.createShowPlaylist(setting1, setting2)    
            
        self.log('makeTypePlaylists invalid channel type: ' + str(chtype))
        return ''    
    
    
    def createNetworkPlaylist(self, network):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'network_' + network + '.xsp')
        
        try:
            fle = FileAccess.open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "episodes", self.getChannelName(1, network))
        network = network.lower()
        added = False

        fle.write('    <rule field="tvshow" operator="is">\n')
        
        for i in range(len(self.showList)):
            if self.threadPause() == False:
                fle.close()
                return ''

            if self.showList[i][1].lower() == network:
                theshow = self.cleanString(self.showList[i][0])                
                fle.write('        <value>' + theshow + '</value>\n')            
                added = True
        
        fle.write('    </rule>\n')
        
        self.writeXSPFooter(fle, self.limit, "random")
        fle.close()

        if added == False:
            return ''
        return flename


    def createShowPlaylist(self, show, setting2):
        order = 'random'

        try:
            setting = int(setting2)
            if setting & MODE_ORDERAIRDATE > 0:
                order = 'episode'
        except Exception,e:
            pass

        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Show_' + show + '_' + order + '.xsp')
        
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, 'episodes', self.getChannelName(6, show))
        show = self.cleanString(show)
        fle.write('    <rule field="tvshow" operator="is">\n')
        fle.write('        <value>' + show + '</value>\n')
        fle.write('    </rule>\n')
        
        self.writeXSPFooter(fle, self.limit, order)
        fle.close()
        return flename

    
    def fillMixedGenreInfo(self):
        if len(self.mixedGenreList) == 0:
            if len(self.showGenreList) == 0:
                self.fillTVInfo()
            if len(self.movieGenreList) == 0:
                self.fillMovieInfo()

            self.mixedGenreList = self.makeMixedList(self.showGenreList, self.movieGenreList)
            self.mixedGenreList.sort(key=lambda x: x.lower())

    
    def makeMixedList(self, list1, list2):
        self.log("makeMixedList")
        newlist = []

        for item in list1:
            curitem = item.lower()

            for a in list2:
                if curitem == a.lower():
                    newlist.append(item)
                    break
        return newlist
    
    
    def createGenreMixedPlaylist(self, genre):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'mixed_' + genre + '.xsp')
        
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        epname = os.path.basename(self.createGenrePlaylist('episodes', 3, genre))
        moname = os.path.basename(self.createGenrePlaylist('movies', 4, genre))
        self.writeXSPHeader(fle, 'mixed', self.getChannelName(5, genre))
        fle.write('    <rule field="playlist" operator="is">' + epname + '</rule>\n')
        fle.write('    <rule field="playlist" operator="is">' + moname + '</rule>\n')
        self.writeXSPFooter(fle, self.limit, "random")
        fle.close()
        return flename


    def createGenrePlaylist(self, pltype, chtype, genre):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + pltype + '_' + genre + '.xsp')
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, pltype, self.getChannelName(chtype, genre))
        genre = self.cleanString(genre)
        fle.write('    <rule field="genre" operator="is">\n')
        fle.write('        <value>' + genre + '</value>\n')
        fle.write('    </rule>\n')
        
        self.writeXSPFooter(fle, self.limit, "random")
        fle.close()
        return flename


    def createStudioPlaylist(self, studio):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Studio_' + studio + '.xsp')
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "movies", self.getChannelName(2, studio))
        studio = self.cleanString(studio)
        fle.write('    <rule field="studio" operator="is">\n')
        fle.write('        <value>' + studio + '</value>\n')
        fle.write('    </rule>\n')
        
        self.writeXSPFooter(fle, self.limit, "random")
        fle.close()
        return flename
        
        
    def createRecentlyAddedTV(self):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'episodes_RecentlyAddedTV.xsp')
        limit = MEDIA_LIMIT[int(REAL_SETTINGS.getSetting('MEDIA_LIMIT'))]
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        fle.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
        fle.write('<smartplaylist type="episodes">\n')
        fle.write('    <name>Recently Added TV</name>\n')
        fle.write('    <match>all</match>\n')
        fle.write('    <rule field="dateadded" operator="inthelast">\n')
        fle.write('        <value>14</value>\n')
        fle.write('    </rule>\n')
        fle.write('    <limit>'+str(limit)+'</limit>\n')
        fle.write('    <order direction="descending">dateadded</order>\n')
        fle.write('</smartplaylist>\n')
        fle.close()
        return flename
        
    
    def createRecentlyAddedMovies(self):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'movies_RecentlyAddedMovies.xsp')
        limit = MEDIA_LIMIT[int(REAL_SETTINGS.getSetting('MEDIA_LIMIT'))]
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        fle.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
        fle.write('<smartplaylist type="movies">\n')
        fle.write('    <name>Recently Added Movies</name>\n')
        fle.write('    <match>all</match>\n')
        fle.write('    <rule field="dateadded" operator="inthelast">\n')
        fle.write('        <value>14</value>\n')
        fle.write('    </rule>\n')
        fle.write('    <limit>'+str(limit)+'</limit>\n')
        fle.write('    <order direction="descending">dateadded</order>\n')
        fle.write('</smartplaylist>\n')
        fle.close()
        return flename


    def createDirectoryPlaylist(self, setting1, setting3, setting4, limit):
        self.log("createDirectoryPlaylist_NEW")
        fileList = []
        LocalLST = []
        LocalFLE = ''
        filecount = 0 
        LiveID = 'other|0|0|False|1|NR|'
        
        if not setting1.endswith('/'):
            setting1 = os.path.join(setting1,'')
            
        LocalLST = self.walk(setting1)

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding Videos", "getting file list")
        
        for i in range(len(LocalLST)):         
            if self.threadPause() == False:
                del fileList[:]
                break
                
            LocalFLE = (LocalLST[i])[0]
            duration = self.videoParser.getVideoLength(LocalFLE)
                                            
            if duration == 0 and LocalFLE[-4:].lower() == 'strm':
                duration = 3600
                self.log("createDirectoryPlaylist, no strm duration found defaulting to 3600")
                    
            if duration > 0:
                filecount += 1
                
                if self.background == False:
                    if filecount == 1:
                        self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding Videos", "added " + str(filecount) + " entry")
                    else:
                        self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding Videos", "added " + str(filecount) + " entries")
                
                title = (os.path.split(LocalFLE)[1])
                title = os.path.splitext(title)[0].replace('.', ' ')
                description = LocalFLE.replace('//','/').replace('/','\\')
                
                tmpstr = str(duration) + ',' + title + "//" + 'Directory Video' + "//" + description + "//" + 'Unknown' + "////" + LiveID + '\n' + (LocalFLE)
                tmpstr = tmpstr[:2036]
                fileList.append(tmpstr)
                    
                if filecount >= limit:
                    break
                    
        if filecount == 0:
            self.log('Unable to access Videos files in ' + setting1)
        return fileList


    def writeXSPHeader(self, fle, pltype, plname):
        fle.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
        fle.write('<smartplaylist type="'+pltype+'">\n')
        plname = self.cleanString(plname)
        fle.write('    <name>'+plname+'</name>\n')
        fle.write('    <match>one</match>\n')


    def writeXSPFooter(self, fle, limit, order):
        if limit > 0:
            fle.write('    <limit>'+str(limit)+'</limit>\n')
        fle.write('    <order direction="ascending">' + order + '</order>\n')
        fle.write('</smartplaylist>\n')
    

    def CleanLabels(self, text):
        self.logDebug('CleanLabels, in = ' + text)
        text = re.sub('\[COLOR (.+?)\]', '', text)
        text = re.sub('\[/COLOR\]', '', text)
        text = re.sub('\[COLOR=(.+?)\]', '', text)
        text = re.sub('\[color (.+?)\]', '', text)
        text = re.sub('\[/color\]', '', text)
        text = re.sub('\[Color=(.+?)\]', '', text)
        text = re.sub('\[/Color\]', '', text)
        text = text.replace("()",'')
        text = text.replace("\ ",'')
        text = text.replace("\\",'')
        text = text.replace("/ ",'')
        text = text.replace("//",'')
        text = text.replace("[B]",'')
        text = text.replace("[/B]",'')
        text = text.replace("[I]",'')
        text = text.replace("[/I]",'')
        text = text.replace("[HD]",'')
        text = text.replace("[CC]",'')
        text = text.replace("[Cc]",'')
        text = text.replace("(SUB)",'')
        text = text.replace("(DUB)",'')
        text = text.replace("\n", "")
        text = text.replace("\r", "")
        text = text.replace("\t", "")
        text = (text.title()).replace("'S","'s")
        self.logDebug('CleanLabels, out = ' + text)
        return text
    
    
    def cleanRating(self, rating):
        self.log("cleanRating")
        rating = rating.replace('Rated ','').replace('US:','').replace('UK:','').replace('Unrated','NR').replace('NotRated','NR').replace('N/A','NR').replace('NA','NR').replace('Approved','NR')
        return rating
        # rating = rating.replace('Unrated','NR').replace('NotRated','NR').replace('N/A','NR').replace('Approved','NR')
    

    def cleanString(self, string):
        newstr = uni(string)
        newstr = newstr.replace('&', '&amp;')
        newstr = newstr.replace('>', '&gt;')
        newstr = newstr.replace('<', '&lt;')
        return uni(newstr)

    
    def uncleanString(self, string):
        self.log("uncleanString")
        newstr = string
        newstr = newstr.replace('&amp;', '&')
        newstr = newstr.replace('&gt;', '>')
        newstr = newstr.replace('&lt;', '<')
        return uni(newstr)
               
            
    def fillMusicInfo(self, sortbycount = False):
        self.log("fillMusicInfo")
        self.musicGenreList = []
        json_query = ('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"properties":["genre"]}, "id": 1}')
        
        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding music", "reading music data")

        json_folder_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.musicGenreList[:]
                return

            match = re.search('"genre" *: *\[(.*?)\]', f)
          
            if match:
                genres = match.group(1).split(',')
               
                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip('"').strip()

                    for g in range(len(self.musicGenreList)):
                        if self.threadPause() == False:
                            del self.musicGenreList[:]
                            return
                            
                        itm = self.musicGenreList[g]

                        if sortbycount:
                            itm = itm[0]

                        if curgenre == itm.lower():
                            found = True

                            if sortbycount:
                                self.musicGenreList[g][1] += 1

                            break

                    if found == False:
                        if sortbycount:
                            self.musicGenreList.append([genre.strip('"').strip(), 1])
                        else:
                            self.musicGenreList.append(genre.strip('"').strip())
    
        if sortbycount:
            self.musicGenreList.sort(key=lambda x: x[1], reverse = True)
        else:
            self.musicGenreList.sort(key=lambda x: x.lower())

        if (len(self.musicGenreList) == 0):
            self.logDebug(json_folder_detail)

        self.log("found genres " + str(self.musicGenreList))
     
    
    def fillTVInfo(self, sortbycount = False):
        self.log("fillTVInfo")
        json_query = ('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties":["studio", "genre"]}, "id": 1}')

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding Videos", "reading TV data")

        json_folder_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.networkList[:]
                del self.showList[:]
                del self.showGenreList[:]
                return

            match = re.search('"studio" *: *\[(.*?)\]', f)
            network = ''

            if match:
                network = (match.group(1).split(','))[0]
                network = network.strip('"').strip()
                found = False

                for item in range(len(self.networkList)):
                    if self.threadPause() == False:
                        del self.networkList[:]
                        del self.showList[:]
                        del self.showGenreList[:]
                        return

                    itm = self.networkList[item]

                    if sortbycount:
                        itm = itm[0]

                    if itm.lower() == network.lower():
                        found = True

                        if sortbycount:
                            self.networkList[item][1] += 1

                        break

                if found == False and len(network) > 0:
                    if sortbycount:
                        self.networkList.append([network, 1])
                    else:
                        self.networkList.append(network)

            match = re.search('"label" *: *"(.*?)",', f)

            if match:
                show = match.group(1).strip()
                self.showList.append([show, network])
                
            match = re.search('"genre" *: *\[(.*?)\]', f)

            if match:
                genres = match.group(1).split(',')
                
                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip('"').strip()

                    for g in range(len(self.showGenreList)):
                        if self.threadPause() == False:
                            del self.networkList[:]
                            del self.showList[:]
                            del self.showGenreList[:]
                            return

                        itm = self.showGenreList[g]

                        if sortbycount:
                            itm = itm[0]

                        if curgenre == itm.lower():
                            found = True

                            if sortbycount:
                                self.showGenreList[g][1] += 1

                            break

                    if found == False:
                        if sortbycount:
                            self.showGenreList.append([genre.strip('"').strip(), 1])
                        else:
                            self.showGenreList.append(genre.strip('"').strip())

        if sortbycount:
            self.networkList.sort(key=lambda x: x[1], reverse = True)
            self.showGenreList.sort(key=lambda x: x[1], reverse = True)
        else:
            self.networkList.sort(key=lambda x: x.lower())
            self.showGenreList.sort(key=lambda x: x.lower())

        if (len(self.showList) == 0) and (len(self.showGenreList) == 0) and (len(self.networkList) == 0):
            self.logDebug(json_folder_detail)

        self.log("found shows " + str(self.showList))
        self.log("found genres " + str(self.showGenreList))
        self.log("fillTVInfo return " + str(self.networkList))


    def fillMovieInfo(self, sortbycount = False):
        self.log("fillMovieInfo")
        studioList = []
        json_query = ('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties":["studio", "genre"]}, "id": 1}')

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding Videos", "reading movie data")

        json_folder_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.movieGenreList[:]
                del self.studioList[:]
                del studioList[:]
                break

            match = re.search('"genre" *: *\[(.*?)\]', f)

            if match:
                genres = match.group(1).split(',')

                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip('"').strip()

                    for g in range(len(self.movieGenreList)):
                        itm = self.movieGenreList[g]

                        if sortbycount:
                            itm = itm[0]

                        if curgenre == itm.lower():
                            found = True

                            if sortbycount:
                                self.movieGenreList[g][1] += 1

                            break

                    if found == False:
                        if sortbycount:
                            self.movieGenreList.append([genre.strip('"').strip(), 1])
                        else:
                            self.movieGenreList.append(genre.strip('"').strip())

            match = re.search('"studio" *: *\[(.*?)\]', f)
           
            if match:
                studios = match.group(1).split(',')
                
                for studio in studios:
                    curstudio = studio.strip('"').strip()
                    found = False

                    for i in range(len(studioList)):
                        if studioList[i][0].lower() == curstudio.lower():
                            studioList[i][1] += 1
                            found = True
                            break

                    if found == False and len(curstudio) > 0:
                        studioList.append([curstudio, 1])

        maxcount = 0

        for i in range(len(studioList)):
            if studioList[i][1] > maxcount:
                maxcount = studioList[i][1]

        bestmatch = 1
        lastmatch = 1000
        counteditems = 0

        for i in range(maxcount, 0, -1):
            itemcount = 0

            for j in range(len(studioList)):
                if studioList[j][1] == i:
                    itemcount += 1

            if abs(itemcount + counteditems - 8) < abs(lastmatch - 8):
                bestmatch = i
                lastmatch = itemcount

            counteditems += itemcount

        if sortbycount:
            studioList.sort(key=lambda x: x[1], reverse=True)
            self.movieGenreList.sort(key=lambda x: x[1], reverse=True)
        else:
            studioList.sort(key=lambda x: x[0].lower())
            self.movieGenreList.sort(key=lambda x: x.lower())

        for i in range(len(studioList)):
            if studioList[i][1] >= bestmatch:
                if sortbycount:
                    self.studioList.append([studioList[i][0], studioList[i][1]])
                else:
                    self.studioList.append(studioList[i][0])

        if (len(self.movieGenreList) == 0) and (len(self.studioList) == 0):
            self.logDebug(json_folder_detail)

        self.log("found genres " + str(self.movieGenreList))
        self.log("fillMovieInfo return " + str(self.studioList))


    def makeMixedList(self, list1, list2):
        self.log("makeMixedList")
        newlist = []

        for item in list1:
            curitem = item.lower()

            for a in list2:
                if curitem == a.lower():
                    newlist.append(item)
                    break

        self.log("makeMixedList return " + str(newlist))
        return newlist
        
        
    # pack to string for playlist
    def packGenreLiveID(self, GenreLiveID):
        self.log("packGenreLiveID, GenreLiveID = " + str(GenreLiveID))
        genre = GenreLiveID[0]
        GenreLiveID.pop(0)
        LiveID = (str(GenreLiveID)).replace("u'",'').replace(',','|').replace('[','').replace(']','').replace("'",'').replace(" ",'') + '|'
        return genre, LiveID
        
        
    # unpack to list for parsing
    def unpackLiveID(self, LiveID):
        self.log("unpackLiveID, LiveID = " + LiveID)
        LiveID = LiveID.split('|')
        return LiveID

        
    def buildFileList(self, dir_name, channel, limit, FleType = 'video'): ##fix music channel todo
        self.log("buildFileList")
        fileList = []
        seasoneplist = []
        file_detail = []
        filecount = 0
        LiveID = 'other|0|0|False|1|NR|'
        json_query = uni('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "%s", "properties":["title","year","mpaa","imdbnumber","description","season","episode","playcount","genre","duration","runtime","showtitle","album","artist","plot","plotoutline","tagline","tvshowid"]}, "id": 1}' % (self.escapeDirJSON(dir_name), FleType))

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding Videos", "querying database")
        
        json_folder_detail = self.sendJSON(json_query)
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in file_detail:
            if self.threadPause() == False:
                del fileList[:]
                break
                
            istvshow = False
            Managed = False
            match = re.search('"file" *: *"(.*?)",', f)
            
            if match:
                if(match.group(1).endswith("/") or match.group(1).endswith("\\")):
                    fileList.extend(self.buildFileList(match.group(1), channel, limit))
                else:
                    f = self.runActions(RULES_ACTION_JSON, channel, f)
                    duration = re.search('"duration" *: *([0-9]*?),', f)
                    
                    # If music duration returned, else 0
                    try:
                        dur = int(duration.group(1))
                    except Exception,e:
                        dur = 0
                        pass
                        
                    # Less accurate duration
                    if dur == 0:
                        duration = re.search('"runtime" *: *([0-9]*?),', f)
                        try:
                            dur = int(duration.group(1))
                        except Exception,e:
                            dur = 0
                            pass
                            
                    # As a last resort use videoParser
                    if dur == 0:
                        try:
                            dur = self.videoParser.getVideoLength(uni(match.group(1)).replace("\\\\", "\\"))
                        except Exception,e:
                            dur = 0
                            pass
 
                    if match.group(1).replace("\\\\", "\\")[-4:].lower() == 'strm':
                        dur = 0

                    self.logDebug("buildFileList, dur = " + str(dur))  
                    
                    try:
                        if dur > 0:
                            filecount += 1
                            seasonval = -1
                            epval = -1

                            if self.background == False:
                                if filecount == 1:
                                    self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding Videos", "added " + str(filecount) + " entry")
                                else:
                                    self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding Videos", "added " + str(filecount) + " entries")
                            
                            tmpstr = str(dur) + ','
                            titles = re.search('"label" *: *"(.*?)"', f)
                            showtitles = re.search('"showtitle" *: *"(.*?)"', f)
                            plots = re.search('"plot" *: *"(.*?)",', f)
                            plotoutlines = re.search('"plotoutline" *: *"(.*?)",', f)
                            years = re.search('"year" *: *([\d.]*\d+)', f)
                            genres = re.search('"genre" *: *\[(.*?)\]', f)
                            playcounts = re.search('"playcount" *: *([\d.]*\d+),', f)
                            imdbnumbers = re.search('"imdbnumber" *: *"(.*?)"', f)
                            ratings = re.search('"mpaa" *: *"(.*?)"', f)
                            descriptions = re.search('"description" *: *"(.*?)"', f)
                            
                            if showtitles != None and len(showtitles.group(1)) > 0:
                                type = 'tvshow'
                                dbids = re.search('"tvshowid" *: *([\d.]*\d+),', f)   
                            else:
                                type = 'movie'
                                dbids = re.search('"id" *: *([\d.]*\d+),', f)

                            # if possible find year by title
                            if years == None and len(years.group(1)) == 0:
                                try:
                                    year = int(((showtitles.group(1)).split(' ('))[1].replace(')',''))
                                except:
                                    try:
                                        year = int(((titles.group(1)).split(' ('))[1].replace(')',''))
                                    except:
                                        year = 0
                                        pass
                            else:
                                year = 0

                            self.logDebug("buildFileList, year = " + str(year))  

                            if genres != None and len(genres.group(1)) > 0:
                                genre = ((genres.group(1).split(',')[0]).replace('"',''))
                            else:
                                genre = 'Unknown'
                            
                            self.logDebug("buildFileList, genre = " + genre)  
                            
                            if playcounts != None and len(playcounts.group(1)) > 0:
                                playcount = playcounts.group(1)
                            else:
                                playcount = 1
                    
                            self.logDebug("buildFileList, playcount = " + str(playcount))  
                            
                            if ratings != None and len(ratings.group(1)) > 0:
                                rating = self.cleanRating(ratings.group(1))
                                if type == 'movie':
                                    rating = rating[0:5]
                                    try:
                                        rating = rating.split(' ')[0]
                                    except:
                                        pass
                            else:
                                rating = 'NR'
                                
                            self.logDebug("buildFileList, rating = " + rating)  
                            
                            if imdbnumbers != None and len(imdbnumbers.group(1)) > 0:
                                imdbnumber = imdbnumbers.group(1)
                            else:
                                imdbnumber = 0
                                
                            self.logDebug("buildFileList, imdbnumber = " + str(imdbnumber))
                            
                            if dbids != None and len(dbids.group(1)) > 0:
                                dbid = dbids.group(1)
                            else:
                                dbid = 0
                                
                            self.logDebug("buildFileList, dbid = " + str(dbid))

                            if plots != None and len(plots.group(1)) > 0:
                                theplot = (plots.group(1)).replace('\\','').replace('\n','')
                            elif descriptions != None and len(descriptions.group(1)) > 0:
                                theplot = (descriptions.group(1)).replace('\\','').replace('\n','')
                            else:
                                theplot = (titles.group(1)).replace('\\','').replace('\n','')
                            
                            try:
                                theplot = (self.trim(theplot, 350, '...'))
                            except Exception,e:
                                theplot = (theplot[:350])

                            # This is a TV show
                            if showtitles != None and len(showtitles.group(1)) > 0:
                                season = re.search('"season" *: *(.*?),', f)
                                episode = re.search('"episode" *: *(.*?),', f)
                                swtitle = (titles.group(1)).replace('\\','')
                                swtitle = (swtitle.split('.', 1)[-1]).replace('. ','')
                                
                                try:
                                    seasonval = int(season.group(1))
                                    epval = int(episode.group(1))
                                    swtitle = (('0' if seasonval < 10 else '') + str(seasonval) + 'x' + ('0' if epval < 10 else '') + str(epval) + ' - ' + (swtitle)).replace('  ',' ')
                                except Exception,e:
                                    self.log("Season/Episode formatting failed" + str(e))
                                    seasonval = -1
                                    epval = -1

                                GenreLiveID = [genre, type, imdbnumber, dbid, Managed, playcount, rating] 
                                genre, LiveID = self.packGenreLiveID(GenreLiveID)
                                tmpstr += (showtitles.group(1)) + "//" + swtitle + "//" + theplot + "//" + genre + "////" + LiveID
                                istvshow = True
                            else:
                                # if '(' not in titles.group(1) and year != 0:
                                    # tmpstr += titles.group(1) + ' (' + str(year) + ')' + "//" 
                                # else:
                                tmpstr += titles.group(1) + "//"
                                album = re.search('"album" *: *"(.*?)"', f)

                                # This is a movie
                                if not album or len(album.group(1)) == 0:
                                    taglines = re.search('"tagline" *: *"(.*?)"', f)
                                    
                                    if taglines and len(taglines.group(1)) > 0:
                                        tmpstr += (taglines.group(1)).replace('\\','')
    
                                    GenreLiveID = [genre, type, imdbnumber, dbid, Managed, playcount, rating]
                                    genre, LiveID = self.packGenreLiveID(GenreLiveID)           
                                    tmpstr += "//" + theplot + "//" + (genre) + "////" + (LiveID)
                                
                                else: #Music
                                    LiveID = 'music|0|0|False|1|NR|'
                                    artist = re.search('"artist" *: *"(.*?)"', f)
                                    tmpstr += album.group(1) + "//" + artist.group(1) + "//" + 'Music' + "////" + LiveID
                            
                            file = unquote(match.group(1))
                            tmpstr = tmpstr
                            tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                            tmpstr = tmpstr + '\n' + file.replace("\\\\", "\\")
                            
                            if self.channels[channel - 1].mode & MODE_ORDERAIRDATE > 0:
                                seasoneplist.append([seasonval, epval, tmpstr])                        
                            else:
                                fileList.append(tmpstr)
                    except Exception,e:
                        self.log('buildFileList, failed...' + str(e))
                        pass
            else:
                continue

        if self.channels[channel - 1].mode & MODE_ORDERAIRDATE > 0:
            seasoneplist.sort(key=lambda seep: seep[1])
            seasoneplist.sort(key=lambda seep: seep[0])

            for seepitem in seasoneplist:
                fileList.append(seepitem[2])

        if filecount == 0:
            self.logDebug(json_folder_detail)

        self.log("buildFileList return")
        return fileList


    def buildMixedFileList(self, dom1, channel, limit):
        self.log('buildMixedFileList')
        fileList = []
        try:
            rules = dom1.getElementsByTagName('rule')
            order = dom1.getElementsByTagName('order')
        except Exception,e:
            self.log('buildMixedFileList Problem parsing playlist ' + filename, xbmc.LOGERROR)
            xml.close()
            
            return fileList

        for rule in rules:
            rulename = rule.childNodes[0].nodeValue

            if FileAccess.exists(xbmc.translatePath('special://profile/playlists/video/') + rulename):
                FileAccess.copy(xbmc.translatePath('special://profile/playlists/video/') + rulename, MADE_CHAN_LOC + rulename)
                fileList.extend(self.buildFileList(MADE_CHAN_LOC + rulename, channel, limit))
            else:
                fileList.extend(self.buildFileList(GEN_CHAN_LOC + rulename, channel, limit))

        self.log("buildMixedFileList returning")
        return fileList

        
    # *Thanks sphere, taken from plugin.video.ted.talks
    # People still using Python <2.7 201303 :(
    def __total_seconds__(self, delta):
        try:
            return delta.total_seconds()
        except AttributeError:
            return float((delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 10 ** 6)) / 10 ** 6

            
    def parsePVRDate(self, tmpDate):
        t = time.strptime(tmpDate, '%Y-%m-%d %H:%M:%S')
        tmpDate = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
        timestamp = calendar.timegm(tmpDate.timetuple())
        local_dt = datetime.datetime.fromtimestamp(timestamp)
        assert tmpDate.resolution >= timedelta(microseconds=1)
        return local_dt.replace(microsecond=tmpDate.microsecond) 

        
    def buildLiveTVFileList(self, setting1, setting2, setting3, setting4, limit):
        self.log("buildLiveTVFileList_NEW")
        showList = []
        chname = (self.getChannelName(8, self.settingChannel))
        now = datetime.datetime.now()
        
        try:
            if setting3 == 'pvr':
                showList = self.fillLiveTVPVR(setting1, setting2, setting3, setting4, chname, limit)
                MSG = 'Listing Unavailable, Check your pvr backend'
        except Exception,e:
            self.log("buildLiveTVFileList, Error: " + str(e))
            pass  
        return showList

            
    def fillLiveTVPVR(self, setting1, setting2, setting3, setting4, chname, limit):
        self.log("fillLiveTVPVR")
        showList = []
        showcount = 0
        json_query = ('{"jsonrpc":"2.0","method":"PVR.GetBroadcasts","params":{"channelid":%s,"properties":["title","plot","plotoutline","starttime","endtime","runtime","genre","episodename","episodenum","episodepart","firstaired","hastimer","parentalrating","thumbnail","rating"]}, "id": 1}' % setting1)
        json_folder_detail = self.sendJSON(json_query)
        detail = re.compile("{(.*?)}", re.DOTALL ).findall(json_folder_detail)
        now = self.parsePVRDate((str(datetime.datetime.utcnow())).split(".")[0])
        
        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding LiveTV", 'parsing ' + chname)

        try:
            for f in detail:
                if self.threadPause() == False:
                    del showList[:]
                    return
                    
                titles = re.search('"title" *: *"(.*?)"', f)
                if titles:
                    title = titles.group(1)
                else:
                    try:
                        labels = re.search('"label" *: *"(.*?)"', f)
                        title = labels.group(1)
                    except:
                        title = None
                
                if title:
                    startDates = re.search('"starttime" *: *"(.*?)",', f)
                    stopDates = re.search('"endtime" *: *"(.*?)",', f)
                    subtitle = 'LiveTV'
                    Managed = False
                    id = 0
                    seasonNumber = 0
                    episodeNumber = 0
                    
                    if startDates:
                        startDate = self.parsePVRDate(startDates.group(1))
                        stopDate = self.parsePVRDate(stopDates.group(1))

                    if now > stopDate:
                        continue

                    runtimes = re.search('"runtime" *: *"(.*?)",', f)
                    #adjust the duration of the current show
                    if now > startDate and now <= stopDate:
                        print ' now > startDate'
                        if runtimes:
                            dur = int(runtimes.group(1)) * 60
                        else:
                            dur = int((stopDate - startDate).seconds)

                    #use the full duration for an upcoming show
                    if now < startDate:
                        print 'now < startDate'
                        if runtimes:
                            dur = int(runtimes.group(1)) * 60
                        else:
                            dur = ((stopDate - startDate).seconds)   
             
                    movie = False
                    genres = re.search('"genre" *: *"(.*?)",', f)
                    if genres:
                        genre = genres.group(1)
                        if genre.lower() == 'movie':
                            movie = True
                    else:
                        genre = 'Unknown'
                        
                    tvtypes = ['Episodic','Series','Sports','News','Paid Programming']
                    if dur >= 7200 and genre not in tvtypes:
                        movie = True
                        
                    if movie == True:
                        type = 'movie'
                    else:
                        type = 'tvshow'

                    try:
                        test = title.split(" *")[1]
                        title = title.split(" *")[0]
                        playcount = 0
                    except Exception,e:
                        playcount = 1
                        pass

                    plots = re.search('"plot" *: *"(.*?)"', f)
                    if plots:
                        description = plots.group(1)
                    else:
                        description = ''

                    ratings = re.search('"rating" *: *"(.*?)"', f)
                    if ratings:
                        rating = ratings.group(1)
                    else:
                        rating = 0
                    
                    # if type == 'tvshow':
                        # episodenames = re.search('"episodename" *: *"(.*?)"', f)
                        # if episodename and len(episodenames) > 0:
                            # episodename = episodenames.group(1)
                        # else:
                            # episodename = ''
                        # episodenums = re.search('"episodenum" *: *"(.*?)"', f)
                        # if episodenums and len(episodenums) > 0:
                            # episodenum = episodenums.group(1) 
                        # else:
                            # episodenum = 0 
                        # episodeparts = re.search('"episodepart" *: *"(.*?)"', f)
                        # if episodeparts and len(episodeparts) > 0:
                            # episodepart = episodeparts.group(1)
                        # else:
                            # episodepart = 0 

                    #filter unwanted ids by title
                    if title == ('Paid Programming') or description == ('Paid Programming'):
                        ignoreParse = True
                    else:
                        ignoreParse = False
                                            
                    if seasonNumber > 0:
                        seasonNumber = '%02d' % int(seasonNumber)
                    
                    if episodeNumber > 0:
                        episodeNumber = '%02d' % int(episodeNumber)
                             
                    try:
                        description = (self.trim(description, 350, '...'))
                    except Exception,e:
                        self.log("description Trim failed" + str(e))
                        description = (description[:350])
                        pass
                            
                    GenreLiveID = [genre,type,id,0,Managed,playcount,rating] 
                    genre, LiveID = self.packGenreLiveID(GenreLiveID) 
                   
                    if type == 'tvshow':
                        episodetitle = (('0' if seasonNumber < 10 else '') + str(seasonNumber) + 'x' + ('0' if episodeNumber < 10 else '') + str(episodeNumber) + ' - '+ (subtitle)).replace('  ',' ')

                        if str(episodetitle[0:5]) == '00x00':
                            episodetitle = episodetitle.split("- ", 1)[-1]
                            
                        tmpstr = str(dur) + ',' + title + "//" + episodetitle + "//" + description + "//" + genre + "//" + str(startDate) + "//" + LiveID + '\n' + setting2
                    
                    else: #Movie
                        tmpstr = str(dur) + ',' + title + "//" + subtitle + "//" + description + "//" + genre + "//" + str(startDate) + "//" + LiveID + '\n' + setting2
                
                    tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                    showList.append(tmpstr)
                    showcount += 1
                    
                    if showcount > limit:
                        break

                    if self.background == False:
                        self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding LiveTV, parsing " + chname, "added " + str(showcount))
        
            if showcount == 0:
                self.log('Unable to find pvr guidedata for ' + setting1)
        except Exception: 
            pass
        return showList

        
    def buildInternetTVFileList(self, setting1, setting2, setting3, setting4):
        self.log('buildInternetTVFileList')
        showList = []
        seasoneplist = []
        showcount = 0
        dur = 0
        LiveID = 'other|0|0|False|1|NR|'  
        
        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding InternetTV", str(setting3))

        title = setting3
        description = setting4
        if not description:
            description = title
        istvshow = True

        if setting1 != '':
            dur = setting1
        else:
            dur = 5400  #90 minute default
            
        self.log("buildInternetTVFileList, CHANNEL: " + str(self.settingChannel) + ", " + title + "  DUR: " + str(dur))
        tmpstr = str(dur) + ',' + title + "//" + "InternetTV" + "//" + description + "//" 'InternetTV' + "////" + LiveID + '\n' + setting2
        tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
        showList.append(tmpstr)
        return showList


    def xmltv_ok(self, setting3):
        self.log("xmltv_ok, setting3 = " + str(setting3))
        self.xmltvValid = True
        return self.xmltvValid
           

    def Valid_ok(self, setting2):
        self.log("Valid_ok_NEW")
        self.Override_ok = REAL_SETTINGS.getSetting('Override_ok') == "true"        
        #plugin check  
        if setting2[0:6] == 'plugin':  
            return self.plugin_ok(setting2)  
        #Override Check# 
        elif self.Override_ok == True:
            return True
        #rtmp check
        elif setting2[0:4] == 'rtmp':
            return self.rtmpDump(setting2)      
        #http check     
        elif setting2[0:4] == 'http':
            return self.url_ok(setting2)
        #strm check  
        elif setting2[-4:] == 'strm':         
            return True
        #pvr check
        elif setting2[0:3] == 'pvr':
            return True  
        #upnp check
        elif setting2[0:4] == 'upnp':
            return True 
        #udp check
        elif setting2[0:3] == 'udp':
            return True  
        #rtsp check
        elif setting2[0:4] == 'rtsp':
            return True  
        #HDHomeRun check
        elif setting2[0:9] == 'hdhomerun':
            return True  

            
    def rtmpDump(self, stream):
        self.rtmpValid = True
        self.log("rtmpValid = " + str(self.rtmpValid))
        return self.rtmpValid
        
                
    def url_ok(self, url):
        self.urlValid = True
        self.log("urlValid = " + str(self.urlValid))
        return self.urlValid
        

    def plugin_ok(self, plugin):
        self.log("plugin_ok, plugin = " + plugin)
        buggalo.addExtraData("plugin_ok, plugin = ", plugin)
        self.PluginFound = False
        self.Pluginvalid = False
        
        try:
            if plugin[0:9] == 'plugin://':
                addon = os.path.split(plugin)[0]
                addon = (plugin.split('/?')[0]).replace("plugin://","")
                addon = splitall(addon)[0]
                self.log("plugin id = " + addon)
            else:
                addon = plugin

            self.PluginFound = xbmc.getCondVisibility('System.HasAddon(%s)' % addon) == 1
            if self.PluginFound == True:
                
                if REAL_SETTINGS.getSetting("plugin_ok_level") == "0":#Low Check
                    self.Pluginvalid = True
                
                elif REAL_SETTINGS.getSetting("plugin_ok_level") == "1":#High Check
                    json_query = ('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory":"%s"}, "id": 1}' % plugin)
                    json_folder_detail = self.sendJSON(json_query)
                    addon_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
                    
                    ## TODO ## Search for exact file, true if found.
                    for f in (addon_detail):
                        file = re.search('"file" *: *"(.*?)"', f)
                        
                    if file != None and len(file.group(1)) > 0:
                        self.Pluginvalid = True     
        except Exception: 
            buggalo.onExceptionRaised() 
            
        self.log("PluginFound = " + str(self.PluginFound))
        return self.Pluginvalid
        

    def trim(self, content, limit, suffix):
        if len(content) <= limit:
            return content
        else:
            return content[:limit].rsplit(' ', 1)[0]+suffix

          
    # Adapted from Ronie's screensaver.picture.slideshow * https://github.com/XBMC-Addons/screensaver.picture.slideshow/blob/master/resources/lib/utils.py    
    def walk(self, path):     
        self.log("walk " + path)
        VIDEO_TYPES = ('.avi', '.mp4', '.m4v', '.3gp', '.3g2', '.f4v', '.mov', '.mkv', '.flv', '.ts', '.m2ts', '.strm')
        video = []
        folders = []
        # multipath support
        if path.startswith('multipath://'):
            # get all paths from the multipath
            paths = path[12:-1].split('/')
            for item in paths:
                folders.append(urllib.unquote_plus(item))
        else:
            folders.append(path)
        for folder in folders:
            if FileAccess.exists(xbmc.translatePath(folder)):
                # get all files and subfolders
                dirs,files = xbmcvfs.listdir(os.path.join(folder,''))
                # natural sort
                convert = lambda text: int(text) if text.isdigit() else text
                alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
                files.sort(key=alphanum_key)
                for item in files:
                    # filter out all video
                    if os.path.splitext(item)[1].lower() in VIDEO_TYPES:
                        video.append([os.path.join(folder,item), ''])
                for item in dirs:
                    # recursively scan all subfolders
                    video += self.walk(os.path.join(folder,item,'')) # make sure paths end with a slash
        return video
        

    # Run rules for a channel
    def runActions(self, action, channel, parameter):
        self.log("runActions " + str(action) + " on channel " + str(channel))
        if channel < 1:
            return

        self.runningActionChannel = channel
        index = 0

        for rule in self.channels[channel - 1].ruleList:
            if rule.actions & action > 0:
                self.runningActionId = index

                if self.background == False:
                    self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "processing rule " + str(index + 1), '')

                parameter = rule.runAction(action, self, parameter)
            index += 1
        
        self.runningActionChannel = 0
        self.runningActionId = 0
        return parameter


    def threadPause(self):
        if threading.activeCount() > 1:
            while self.threadPaused == True and self.myOverlay.isExiting == False:
                time.sleep(self.sleepTime)

            # This will fail when using config.py
            try:
                if self.myOverlay.isExiting == True:
                    self.log("IsExiting")
                    return False
            except Exception,e:
                pass
                
        return True


    def escapeDirJSON(self, dir_name):
        mydir = uni(dir_name)

        if (mydir.find(":")):
            mydir = mydir.replace("\\", "\\\\")
        return mydir


    def getSmartPlaylistType(self, dom):
        self.log('getSmartPlaylistType')

        try:
            pltype = dom.getElementsByTagName('smartplaylist')
            return pltype[0].attributes['type'].value
        except Exception,e:
            self.log("Unable to get the playlist type.", xbmc.LOGERROR)
            return ''
        
        
    def findZap2itID(self, CHname, filename):
        if not CHname:
            CHname = 'Unknown'
        self.log("findZap2itID, CHname = " + CHname)
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        orgCHname = CHname
        XMLTVMatchlst = []
        sorted_XMLTVMatchlst = []
        found = False
        try:
            self.log("findZap2itID, pvr backend")
            if not self.cached_json_detailed_xmltvChannels_pvr:
                self.log("findZap2itID, no cached_json_detailed_xmltvChannels")
                json_query = uni('{"jsonrpc":"2.0","method":"PVR.GetChannels","params":{"channelgroupid":2,"properties":["thumbnail"]},"id": 1 }')
                json_detail = self.sendJSON(json_query)
                self.cached_json_detailed_xmltvChannels_pvr = re.compile( "{(.*?)}", re.DOTALL ).findall(json_detail)
            file_detail = self.cached_json_detailed_xmltvChannels_pvr

            for f in file_detail:
                CHids = re.search('"channelid" *: *(.*?),', f)
                dnames = re.search('"label" *: *"(.*?)"', f)
                thumbs = re.search('"thumbnail" *: *"(.*?)"', f)
               
                if CHids and dnames:
                    CHid = CHids.group(1)
                    dname = dnames.group(1)
                                
                    CHname = CHname.replace('-DT','DT').replace(' DT','DT').replace('DT','').replace('-HD','HD').replace(' HD','HD').replace('HD','').replace('-SD','SD').replace(' SD','SD').replace('SD','')
                    matchLST = [CHname.upper(), 'W'+CHname.upper(), orgCHname, 'W'+orgCHname.upper()]
                    self.logDebug("findZap2itID, Cleaned CHname = " + CHname)

                    dnameID = dname + ' : ' + CHid
                    self.logDebug("findZap2itID, dnameID = " + dnameID)
                    XMLTVMatchlst.append(dnameID)

            sorted_XMLTVMatchlst = sorted_nicely(XMLTVMatchlst)            
            for n in range(len(sorted_XMLTVMatchlst)):
                CHid = '0'
                found = False
                dnameID = sorted_XMLTVMatchlst[n]
                dname = dnameID.split(' : ')[0]
                CHid = dnameID.split(' : ')[1]
                
                if dname.upper() in matchLST: 
                    self.log("findZap2itID, Match Found: " + str(CHname.upper()) +' == '+ str(dname.upper()) + ' , #' + str(CHid))  
                    found = True
                    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
                    return orgCHname, CHid 
                    
            if not found:
                xbmc.executebuiltin( "Dialog.Close(busydialog)" )
                self.log("findZap2itID, No Match Found: " + str(CHname.upper()) +' == '+ str(dname.upper()) + ' ' + str(CHid))
                select = selectDialog(sorted_XMLTVMatchlst, 'Select matching id to [B]%s[/B]' % orgCHname)
                dnameID = sorted_XMLTVMatchlst[select]
                CHid = dnameID.split(' : ')[1]
                return orgCHname, CHid
        except Exception: 
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            buggalo.onExceptionRaised()

            
    def XBMCversion(self):
        json_query = uni('{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')
        json_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_detail)
        
        for f in detail:
            majors = re.search('"major" *: *([0-9]*?),', f)
            if majors:
                major = int(majors.group(1))

        if major == 13:
            version = 'Gotham'
        elif major < 13:
            version = 'Frodo'
        else:
            version = 'Helix'
            
        self.log('XBMCversion = ' + version)
        return version
        
        
    def fillFavourites(self):
        self.log('fillFavourites')
        json_query = uni('{"jsonrpc":"2.0","method":"Favourites.GetFavourites","params":{"properties":["path"]},"id":3}')
        json_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_detail)
        TMPfavouritesList = []

        for f in detail:
            paths = re.search('"path" *: *"(.*?)",', f)
            names = re.search('"title" *: *"(.*?)",', f)
            types = re.search('"type" *: *"(.*?)"', f)
            if types != None and len(types.group(1)) > 0:
                type = types.group(1)
                if type == 'media' and names and paths:
                    name = self.CleanLabels(names.group(1))
                    path = paths.group(1)
                    TMPfavouritesList.append(name+','+path)  

        SortedFavouritesList = sorted_nicely(TMPfavouritesList)
        for i in range(len(SortedFavouritesList)):  
            self.FavouritesNameList.append((SortedFavouritesList[i]).split(',')[0])  
            self.FavouritesPathList.append((SortedFavouritesList[i]).split(',')[1])          