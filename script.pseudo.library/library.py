#   Copyright (C) 2013 Lunatixz
#
#
# This file is part of PseudoLibrary.
#
# PseudoLibrary is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoLibrary is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoLibrary.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import httplib, urllib, urllib2, feedparser, socket, json
import subprocess, os, sys, re, shutil
import time, datetime

from urllib2 import unquote
from xml.etree import ElementTree as ET
from xml.dom.minidom import parse, parseString
from FileAccess import FileAccess

# metahandler plugin import
try:
    from metahandler import metahandlers
except Exception,e:  
    pass
      
# Commoncache plugin import
try:
    import StorageServer
except Exception,e:
    import storageserverdummy as StorageServer
 
# Plugin Info
ADDON_ID = 'script.pseudo.library'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_ID = REAL_SETTINGS.getAddonInfo('id')
ADDON_NAME = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
profile = xbmc.translatePath(REAL_SETTINGS.getAddonInfo('profile').decode('utf-8'))
xbmc.log(ADDON_ID +' '+ ADDON_NAME +' '+ ADDON_PATH +' '+ ADDON_VERSION)

# Globals
cache = StorageServer.StorageServer("plugin://script.pseudo.library/" + "cache",1)
THUMB = REAL_SETTINGS.getAddonInfo('icon')
dlg = xbmcgui.Dialog()
Delay_INT = [0,5,10,15,20]
Refresh_INT = [2,4,6,12,24,48,72]

class library:

    def __init__(self):
        self.httpJSON = True
        self.discoveredWebServer = False
        self.background = True
        self.addonLST = []
        
        if not REAL_SETTINGS.getSetting("STRM_LOC"):
            #Set Default Strm Location
            Default_LOC = os.path.join(profile,'Strms')
            #Set RealSetting Default STRM Location
            REAL_SETTINGS.setSetting("STRM_LOC",Default_LOC)

            
    def readSettings(self, config, background):
        print 'PseudoLibrary - readSettings'
        #Check if readSettings already running (Service)
        REAL_SETTINGS.setSetting("SanityCheck","true")
        MSG = ''
        config = xbmc.translatePath(config)
        STRM_LOC = REAL_SETTINGS.getSetting('STRM_LOC')
        Settings2 = os.path.join(config,'settings2.xml')
        print 'PseudoLibrary - ' + Settings2
        #Enable XBMC Dialogue or null?
        self.background = background
        
        # Clear Folder
        if REAL_SETTINGS.getSetting("Clear_Folder") == "true":
            try:
                shutil.rmtree(STRM_LOC)
                REAL_SETTINGS.setSetting("Clear_Folder","false")
                xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoLibrary", "Strm Folder Cleared", 4000, THUMB) )
            except Exception,e:
                pass

        if self.background == False:
            self.updateDialog = xbmcgui.DialogProgress()
            self.updateDialogProgress = 0
            self.updateDialogProgressCount = 0
            self.updateDialog.create("PseudoLibrary", "Initializing")
            self.updateDialog.update(0, "Initializing")
        
        #parse internal list
        if not xbmcvfs.exists(Settings2):
            print 'PseudoLibrary - readSettings, creating settings2'
            
            #create settings2.xml
            try:
                f = open(Settings2, "w")
                f.write("Genre|Type|Source|Exclusion,Exclusion|Limit|ALTSwitch|Name|Rules\n")
                f.close
            except:
                MSG = "No Configuration File Found!, Check settings2.xml"
                pass
        else:
            #read from list
            print 'PseudoLibrary - readSettings, reading settings2'
            
            try:
                f = open(Settings2, 'r')
                Settings = f.readlines()
                f.close

                if self.background == False:
                    self.updateDialog.update(self.updateDialogProgress, "Reading Configurations", "Parsing Internal List", "")
                
                for i in range(len(Settings)):
                    lineLST = Settings[i]
                    line = lineLST.split("|")
                    StrmType = str(line[0])
                    FolderName = str(line[6]).replace('\n','')  
            except:
                MSG = "Configuration Error!, Check settings2.xml"
                pass

        if MSG:
            xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoLibrary", MSG, 4000, THUMB) )
            
        if REAL_SETTINGS.getSetting('CN_Enable') == 'true': 
            print 'PseudoLibrary - readSettings, Recommended List Enabled'
            #parse external list
            genre_filter = []
            url = 'https://pseudotv-live-community.googlecode.com/svn/addons.xml'
            url1 = 'https://pseudotv-live-community.googlecode.com/svn/playon.xml'
            
            if self.background == False:
                self.updateDialog.update(self.updateDialogProgress, "Reading Configurations", "Parsing Internal List", "")
                
            #create genre_filter list
            if REAL_SETTINGS.getSetting("CN_TV") == "true":
                genre_filter.append('TV') 
            if REAL_SETTINGS.getSetting("CN_Movies") == "true":
                genre_filter.append('Movies') 
            if REAL_SETTINGS.getSetting("CN_Episodes") == "true":
                genre_filter.append('Episodes') 
            if REAL_SETTINGS.getSetting("CN_Sports") == "true":
                genre_filter.append('Sports') 
            if REAL_SETTINGS.getSetting("CN_News") == "true":
                genre_filter.append('News') 
            if REAL_SETTINGS.getSetting("CN_Kids") == "true":
                genre_filter.append('Kids') 
            if REAL_SETTINGS.getSetting("CN_Music") == "true":
                genre_filter.append('Music') 
            if REAL_SETTINGS.getSetting("CN_Other") == "true":
                genre_filter.append('Other') 
                    
            data = self.OpenURL(url) #pluging
            data1 = self.OpenURL(url1) #playon
            data = data + data1
            data = data[2:] #remove first two unwanted lines
            data = ([x for x in data if x != '']) #remove empty lines    
                
            try:
                for i in range(len(data)):
                    lineLST = data[i]
                    line = lineLST.split("|")
                    Genre = line[0]
                    FolderName = line[5]
                    
                    #append wanted items by genre
                    if Genre in genre_filter:
                        Settings.append(lineLST)
            except:
                pass

        try:
            for n in range(len(Settings)):
                line = ((Settings[n]).replace('\n','').replace('""',"")).split('|')
                StrmType = line[0]
                BuildType = (line[1]).replace('15','Plugin').replace('16','Playon')
                setting1 = (line[2]).replace('plugin://','').replace('upnp://','')
                setting2 = (line[3]).replace('plugin://','')
                setting3 = line[4]
                setting4 = line[5]
                FolderName = line[6]
                if BuildType.lower() == 'plugin':
                    setting1 = 'plugin://' + setting1
                    self.BuildPluginFileList(StrmType, BuildType, setting1, setting2, setting3, setting4, FolderName)
                elif BuildType.lower() == 'playon' or BuildType.lower() == 'upnp':
                    self.BuildPlayonFileList(StrmType, BuildType, setting1, setting2, setting3, setting4, FolderName)
                elif BuildType.lower() == 'youtube':
                    self.createYoutubeFilelist(StrmType, BuildType, setting1, setting2, setting3, setting4, FolderName) 
                # elif BuildType.lower() == 'upnp':
                    # setting1 = 'upnp://' + setting1
        except:
            pass

        REAL_SETTINGS.setSetting("SanityCheck","false")
        
        if REAL_SETTINGS.getSetting("Automatic_Update_Folder") == "true":
            xbmc.executebuiltin("UpdateLibrary(video,[%s])" % (STRM_LOC))
            # http://localhost:8080/jsonrpc?request={"jsonrpc":"2.0","method":"VideoLibrary.Scan","params":{"directory":"strmloc"},"id":3}
            
        if REAL_SETTINGS.getSetting("Automatic_Clean_Folder") == "true":
            xbmc.executebuiltin("CleanLibrary(video)")
            # http://localhost:8080/jsonrpc?request={"jsonrpc":"2.0","method":"VideoLibrary.Clean","params":{},"id":2}

        self.updateDialogProgress = 100
        
            
    def BuildPluginFileList(self, StrmType, BuildType, setting1, setting2, setting3, setting4, FolderName):
        print "BuildPluginFileList"
        showList = []
        DetailLST = []
        DetailLST_CHK = []
        self.dircount = 0
        self.filecount = 0
        # self.updateDialogProgressCount = self.updateDialogProgressCount + self.filecount + self.dircount
        limit = int(setting3)
        Pluginvalid = self.plugin_ok(setting1)
        
        if Pluginvalid != False:
            try:
                Directs = (setting1.split('/')) # split folders
                Directs = ([x for x in Directs if x != '']) # remove empty elements
                plugins = Directs[1] # element 1 in split is plugin name
                Directs = Directs[2:] # slice two unwanted elements. ie (plugin:, plugin name)
                plugin = 'plugin://' + plugins
                PluginName = plugins.replace('plugin.video.','').replace('plugin.program.','').replace('/','')
            except:
                Directs = []
                pass

            try:
                excludeLST = setting2.split(',')
                excludeLST = ([x.lower() for x in excludeLST if x != '']) # remove empty elements
            except:
                excludeLST = []
                pass
                
            #filter out unwanted folders
            excludeLST += ['back','previous','home','create new super folder','explore favourites','explore  favourites','explore xbmc favourites','explore kodi favourites','isearch','search','clips','seasons','trailers']
            # print "BuildPluginFileList, excludeLST = " + str(excludeLST)
            
            if self.background == False:
                self.updateDialog.update(self.updateDialogProgress, "Parsing" + ": " + BuildType, PluginName, "")
                                 
            Match = True
            while Match:

                DetailLST = self.PluginInfo(plugin)

                #Plugin listitems return parent list during error, catch repeat list and end loops.
                if DetailLST_CHK == DetailLST:
                    print "BuildPluginFileList, duplicate return breaking loop"
                    break
                else:
                    DetailLST_CHK = DetailLST

                #end while when no more directories to walk
                if len(Directs) <= 1:
                    Match = False

                try:
                    for i in range(len(DetailLST)):   
                        # self.updateDialogProgress = i * 1 // self.updateDialogProgressCount
                        Detail = (DetailLST[i]).split(',')
                        filetype = Detail[0]
                        title = Detail[1]
                        genre = Detail[2]
                        dur = Detail[3]
                        description = Detail[4]
                        file = Detail[5]
                        
                        if self.background == False:
                            self.updateDialog.update(self.updateDialogProgress, "Parsing" + ": " + BuildType, PluginName, "found " + str(Directs[0]))  
                        
                        if title.lower() not in excludeLST and title != '':
                            if filetype == 'directory':
                                CurDirect = self.CleanLabels(Directs[0])
                                if CurDirect.lower() == title.lower():
                                    print 'PseudoLibrary - directory match'
                                    LastName = CurDirect
                                    Directs.pop(0) #remove old directory, search next element
                                    plugin = file
                                    break          
                except:
                    print "BuildPluginFileList, DetailLST Empty"
                    LastName = FolderName
                    pass
                    
        
            
            #all directories found, walk final folder
            if len(Directs) == 0:
                print "BuildPluginFileList, Final folder found walk root"
                # print plugin, excludeLST, limit, StrmType, BuildType, 'video', FolderName
                self.PluginWalk(plugin, excludeLST, limit, StrmType, BuildType, 'video', FolderName, LastName)
                    
                    
    def BuildPlayonFileList(self, StrmType, BuildType, setting1, setting2, setting3, setting4, FolderName):
        print ("BuildPlayonFileList")
        showList = []
        DetailLST = []
        DetailLST_CHK = []
        self.dircount = 0
        self.filecount = 0
        # self.updateDialogProgressCount = self.updateDialogProgressCount + self.filecount + self.dircount
        limit = int(setting3)
        upnpID = self.playon_player()

        if upnpID != False:
            try:
                Directs = (setting1.split('/')) # split folders
                Directs = ([x for x in Directs if x != '']) # remove empty elements
                PluginName = Directs[0]
            except:
                Directs = []
                PluginName = setting1
                pass

            try:
                excludeLST = setting2.split(',')
                excludeLST = ([x.lower() for x in excludeLST if x != '']) # remove empty elements
            except:
                excludeLST = []
                pass
                
            #filter out unwanted folders
            excludeLST += ['back','previous','home','create new super folder','explore favourites','explore  favourites','explore xbmc favourites','explore kodi favourites','isearch','search','clips','seasons','trailers']
            # print "BuildPlayonFileList, excludeLST = " + str(excludeLST)
                
            if self.background == False:
                self.updateDialog.update(self.updateDialogProgress, "Parsing" + ": " + BuildType, PluginName, "")
                
            Match = True
            while Match:
                
                DetailLST = self.PluginInfo(upnpID)

                #Plugin listitems return parent list during error, catch repeat list and end loops.
                if DetailLST_CHK == DetailLST:
                    print "BuildPlayonFileList, duplicate return breaking loop"
                    break
                else:
                    DetailLST_CHK = DetailLST
                    
                #end while when no more directories to walk
                if len(Directs) <= 1:
                    Match = False
                
                try:
                    for i in range(len(DetailLST)):
                        # self.updateDialogProgress = i * 1 // self.updateDialogProgressCount
                        Detail = (DetailLST[i]).split(',')
                        filetype = Detail[0]
                        title = Detail[1]
                        genre = Detail[2]
                        dur = Detail[3]
                        description = Detail[4]
                        file = Detail[5]       
                        
                        if self.background == False:
                            self.updateDialog.update(self.updateDialogProgress, "Parsing" + ": " + BuildType, PluginName, "found " + str(Directs[0]))  
                        
                        if title.lower() not in excludeLST and title != '':
                            if filetype == 'directory':
                                CurDirect = self.CleanLabels(Directs[0])
                                if CurDirect.lower() == title.lower():
                                    print 'PseudoLibrary - directory match'
                                    LastName = CurDirect
                                    Directs.pop(0) #remove old directory, search next element
                                    upnpID = file
                                    break
                except:
                    print 'PseudoLibrary - BuildPlayonFileList, DetailLST Empty'
                    LastName = FolderName
                    pass

        #all directories found, walk final folder
        if len(Directs) == 0:
            print "BuildPlayonFileList, Final folder found walk root"
            # print upnpID, excludeLST, limit, StrmType, BuildType, 'video', DirName
            self.PluginWalk(upnpID, excludeLST, limit, StrmType, BuildType, 'video', FolderName, LastName)

            
    #return plugin query, not tmpstr
    def PluginQuery(self, path): 
        print "PluginQuery" 
        FleType = 'video'
        json_query = self.uni('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "%s", "properties":["title","year","mpaa","imdbnumber","description","season","episode","playcount","genre","duration","runtime","showtitle","album","artist","plot","plotoutline","tagline"]}, "id": 1}' % (self.escapeDirJSON(path), FleType))
        json_folder_detail = self.sendJSON(json_query)
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
        return file_detail
    
    
    #Parse Plugin, return essential information. Not tmpstr
    def PluginInfo(self, path):
        print 'PseudoLibrary - PluginInfo'
        json_query = self.uni('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","properties":["genre","runtime","description"]},"id":1}' % ( (path),))
        json_folder_detail = self.sendJSON(json_query)
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
        Detail = ''
        DetailLST = []
        PluginName = os.path.split(path)[0]

        #run through each result in json return
        for f in (file_detail):
            filetype = re.search('"filetype" *: *"(.*?)"', f)
            label = re.search('"label" *: *"(.*?)"', f)
            genre = re.search('"genre" *: *"(.*?)"', f)
            runtime = re.search('"runtime" *: *([0-9]*?),', f)
            description = re.search('"description" *: *"(.*?)"', f)
            file = re.search('"file" *: *"(.*?)"', f)

            #if core values have info, proceed
            if filetype and file and label:
                filetype = filetype.group(1)
                title = (label.group(1)).replace(',',' ')
                file = file.group(1)

                try:
                    genre = genre.group(1)
                except:
                    genre = 'Unknown'
                    pass

                if genre == '':
                    genre = 'Unknown'

                try:
                    runtime = runtime.group(1)
                except:
                    runtime = 0
                    pass

                if runtime == 0 or runtime == '':
                    runtime = 1800

                try:
                    description = (description.group(1)).replace(',',' ')
                except:
                    description = PluginName
                    pass

                if description == '':
                    description = PluginName

                if title != '':
                    Detail = ((filetype + ',' + title + ',' + genre + ',' + str(runtime) + ',' + description + ',' + file)).replace(',,',',')
                    DetailLST.append(Detail)

        print 'PseudoLibrary - pluginInfo Return'
        return DetailLST
    
 
    #recursively walk through plugin directories, return tmpstr of all files found.
    def PluginWalk(self, path, excludeLST, limit, StrmType, BuildType, FleType, DirName, LastName):
        print "PluginWalk"
        dirlimit = int(limit * 2)
        tmpstr = ''
        LiveID = 'tvshow|0|0|False|1|NR|'
        fileList = []
        dirs = []
        Managed = False
        PluginPath = str(os.path.split(path)[0])
        PluginName = PluginPath.replace('plugin://plugin.video.','').replace('plugin://plugin.program.','')
        # youtube_plugin = self.youtube_player()
        xType = BuildType
        
        json_query = self.uni('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "%s", "properties":["title","year","mpaa","imdbnumber","description","season","episode","playcount","genre","duration","runtime","showtitle","album","artist","plot","plotoutline","tagline"]}, "id": 1}' % ((path), FleType))
        json_folder_detail = self.sendJSON(json_query)
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
        
        try:       
            if xType == '':    
                xName = xType
                PlugCHK = xType
            elif xType.lower() == 'playon':
                xName = (path.split('/')[3]).split('-')[0]
                PlugCHK = xType
            else:
                xName = PluginName
                PlugCHK = PluginPath.replace('plugin://','')
                
            #run through each result in json return
            for f in (file_detail):
                istvshow = False
                durations = re.search('"duration" *: *([0-9]*?),', f)
                runtimes = re.search('"runtime" *: *([0-9]*?),', f)
                filetypes = re.search('"filetype" *: *"(.*?)"', f)
                labels = re.search('"label" *: *"(.*?)"', f)
                files = re.search('"file" *: *"(.*?)"', f)

                # self.updateDialogProgressCount = self.updateDialogProgressCount + self.filecount + self.dircount
                
                #if core variables have info proceed
                if filetypes and labels and files:
                    filetype = filetypes.group(1)
                    file = files.group(1)
                    label = labels.group(1)
                    label = self.CleanLabels(label)
                    
                    if label.lower() not in excludeLST and label != '':

                        if filetype == 'directory':
                            print 'PseudoLibrary - PluginWalk, directory'

                            #try to speed up parsing by not over searching directories when media limit is low
                            if self.filecount < limit and self.dircount < dirlimit:
                                
                                if file[0:4] != 'upnp':
                                    #if no return, try unquote
                                    if not self.PluginInfo(file):
                                        print 'PseudoLibrary - unquote'
                                        file = unquote(file).replace('",return)','')
                                        #remove unwanted reference to super.favorites plugin
                                        try:
                                            file = (file.split('ActivateWindow(10025,"')[1])
                                        except:
                                            pass

                                if self.background == False:
                                    self.updateDialog.update(self.updateDialogProgress, "Parsing" + ": " + BuildType, xName, "found " + xName)  
                                
                                dirs.append(file)
                                self.dircount += 1
                                print "PluginWalk, dircount = " + str(self.dircount) +'/'+ str(dirlimit)
                            else:
                                self.dircount = 0
                                break

                        elif filetype == 'file':
                            print 'PseudoLibrary - PluginWalk, file'

                            if self.filecount < limit:

                                #Remove PlayMedia to keep link from launching
                                try:
                                    file = ((file.split('PlayMedia%28%22'))[1]).replace('%22%29','')
                                except:
                                    try:
                                        file = ((file.split('PlayMedia("'))[1]).replace('")','')
                                    except:
                                        pass

                                if file.startswith('plugin%3A%2F%2F'):
                                    print 'PseudoLibrary - unquote'
                                    file = unquote(file).replace('",return)','')

                                # If music duration returned, else 0
                                try:
                                    dur = int(durations.group(1))
                                except Exception,e:
                                    dur = 0

                                if dur == 0:
                                    try:
                                        dur = int(runtimes.group(1))
                                    except Exception,e:
                                        dur = 3600

                                    if not runtimes or dur == 0:
                                        dur = 3600

                                #correct playon default duration
                                if dur == 18000:
                                    dur = 3600

                                print 'PseudoLibrary - PluginWalk, dur = ' + str(dur)

                                if dur > 0:
                                    self.filecount += 1
                                    # self.updateDialogProgress = i * 1 // self.updateDialogProgressCount
                                    print "PluginWalk, filecount = " + str(self.filecount) +'/'+ str(limit)

                                    tmpstr = str(dur) + ','
                                    labels = re.search('"label" *: *"(.*?)"', f)
                                    titles = re.search('"title" *: *"(.*?)"', f)
                                    showtitles = re.search('"showtitle" *: *"(.*?)"', f)
                                    plots = re.search('"plot" *: *"(.*?)",', f)
                                    plotoutlines = re.search('"plotoutline" *: *"(.*?)",', f)
                                    years = re.search('"year" *: *([0-9]*?) *(.*?)', f)
                                    genres = re.search('"genre" *: *\[(.*?)\]', f)
                                    playcounts = re.search('"playcount" *: *([0-9]*?),', f)
                                    imdbnumbers = re.search('"imdbnumber" *: *"(.*?)"', f)
                                    ratings = re.search('"mpaa" *: *"(.*?)"', f)
                                    descriptions = re.search('"description" *: *"(.*?)"', f)
                                    episodes = re.search('"episode" *: *(.*?),', f)

                                    if (episodes != None and episodes.group(1) != '-1') and showtitles != None and len(showtitles.group(1)) > 0:
                                        type = 'tvshow'
                                        dbids = re.search('"tvshowid" *: *([0-9]*?),', f)
                                        FolderName = showtitles.group(1)
                                    else:
                                        type = 'movie'
                                        dbids = re.search('"movieid" *: *([0-9]*?),', f)
                                        FolderName = label

                                    if self.background == False:
                                        if self.filecount == 1:
                                            self.updateDialog.update(self.updateDialogProgress, "Parsing" + ": " + BuildType, FolderName, "added " + str(self.filecount) + " entry")
                                        else:
                                            self.updateDialog.update(self.updateDialogProgress, "Parsing" + ": " + BuildType, FolderName, "added " + str(self.filecount) + " entries")

                                    if years == None or len(years.group(1)) == 0:
                                        try:
                                            year = int(((showtitles.group(1)).split(' ('))[1].replace(')',''))
                                        except Exception,e:
                                            try:
                                                year = int(((labels.group(1)).split(' ('))[1].replace(')',''))
                                            except:
                                                year = 0
                                                pass
                                    else:
                                        year = 0

                                    if genres != None and len(genres.group(1)) > 0:
                                        genre = ((genres.group(1).split(',')[0]).replace('"',''))
                                    else:
                                        genre = 'Unknown'

                                    if playcounts != None and len(playcounts.group(1)) > 0:
                                        playcount = playcounts.group(1)
                                    else:
                                        playcount = 1

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

                                    if imdbnumbers != None and len(imdbnumbers.group(1)) > 0:
                                        imdbnumber = imdbnumbers.group(1)
                                    else:
                                        imdbnumber = 0

                                    if dbids != None and len(dbids.group(1)) > 0:
                                        dbid = dbids.group(1)
                                    else:
                                        dbid = 0

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

                                    #remove // because interferes with playlist split.
                                    theplot = self.CleanLabels(theplot)

                                    # This is a TV show
                                    if (episodes != None and episodes.group(1) != '-1') and showtitles != None and len(showtitles.group(1)) > 0:
                                        seasons = re.search('"season" *: *(.*?),', f)
                                        episodes = re.search('"episode" *: *(.*?),', f)
                                        swtitle = (labels.group(1)).replace('\\','')

                                        try:
                                            seasonval = int(seasons.group(1))
                                            epval = int(episodes.group(1))
                                        except:
                                            seasonval = -1
                                            epval = -1
                                            pass
                                            
                                        if seasonval > 0 and epval != -1:
                                            try:
                                                eptitles = swtitle.split(' - ')[1]
                                            except:
                                                try:
                                                    eptitles = swtitle.split(' . ')[1]
                                                except:
                                                    eptitles = swtitle
                                                    pass
                                        else:
                                            #no season, episode meta. try to extract from swtitle
                                            try:
                                                #S01E01 - eptitle or s01e01 - eptitle
                                                SEinfo = (swtitle.split(' - ')[0]).replace('S','s').replace('E','e')
                                                seasonval = SEinfo.split('e')[0].replace('s','')
                                                epval = SEinfo.split('e')[1]
                                                eptitles = (swtitle.split('- ', 1)[1])
                                            except:
                                                try:
                                                    #2x01 - eptitle or #2X01 - eptitle
                                                    SEinfo = (swtitle.split(' -')[0]).replace('X','x')
                                                    seasonval = SEinfo.split('x')[0]
                                                    epval = SEinfo.split('x')[1]
                                                    eptitles = (swtitle.split('- ', 1)[1])
                                                except:
                                                    try:
                                                        #2x01 . eptitle or #2X01 . eptitle
                                                        SEinfo = (swtitle.split(' . ',1)[0]).replace('X','x')
                                                        seasonval = SEinfo.split('x')[0]
                                                        epval = SEinfo.split('x')[1]
                                                        eptitles = (swtitle.split(' . ', 1)[1])
                                                    except:
                                                        eptitles = swtitle
                                                        seasonval = -1
                                                        epval = -1
                                                        pass

                                        if seasonval > 0 and epval > 0:
                                            swtitle = (('0' if seasonval < 10 else '') + str(seasonval) + 'x' + ('0' if epval < 10 else '') + str(epval) + ' - ' + (eptitles)).replace('  ',' ')
                                        else:
                                            swtitle = swtitle.replace(' . ',' - ')

                                        showtitle = (showtitles.group(1))
                                        showtitle = self.CleanLabels(showtitle)
                                        
                                        # if PlugCHK in DYNAMIC_PLUGIN_TV:
                                            # print 'PseudoLibrary - DYNAMIC_PLUGIN_TV'

                                            # if REAL_SETTINGS.getSetting('EnhancedGuideData') == 'true':
                                                # print 'PseudoLibrary - EnhancedGuideData'

                                                # if imdbnumber == 0:
                                                    # imdbnumber = self.getTVDBID(showtitle, year)

                                                # if genre == 'Unknown':
                                                    # genre = (self.getGenre(type, showtitle, year))

                                                # if rating == 'NR':
                                                    # rating = (self.getRating(type, showtitle, year, imdbnumber))
                                                    # rating = self.cleanRating(rating)

                                            # GenreLiveID = [genre, type, imdbnumber, dbid, Managed, 1, rating]
                                            # genre, LiveID = self.packGenreLiveID(GenreLiveID)

                                        swtitle = self.CleanLabels(swtitle)
                                        theplot = self.CleanLabels(theplot)
                                        tmpstr += showtitle + "//" + swtitle + "//" + theplot + "//" + genre + "////" + LiveID
                                        istvshow = True

                                    else:

                                        if labels:
                                            label = (labels.group(1))
                                            label = self.CleanLabels(label)
                                            
                                        if titles:
                                            title = (titles.group(1))
                                            title = self.CleanLabels(title)
                                            
                                        tmpstr += label + "//"

                                        album = re.search('"album" *: *"(.*?)"', f)

                                        # This is a movie
                                        if not album or len(album.group(1)) == 0:
                                            taglines = re.search('"tagline" *: *"(.*?)"', f)

                                            if taglines != None and len(taglines.group(1)) > 0:
                                                tagline = (taglines.group(1))
                                                tagline = self.CleanLabels(tagline)
                                                tmpstr += tagline
                                            else:
                                                tmpstr += ''

                                            # if PlugCHK in DYNAMIC_PLUGIN_MOVIE:
                                                # print 'PseudoLibrary - DYNAMIC_PLUGIN_MOVIE'

                                                # if REAL_SETTINGS.getSetting('EnhancedGuideData') == 'true':
                                                    # print 'PseudoLibrary - EnhancedGuideData'

                                                    # try:
                                                        # showtitle = label.split(' (')[0]
                                                        # year = (label.split(' (')[1]).replace(')','')
                                                    # except:
                                                        # showtitle = label
                                                        # year = ''
                                                        # pass

                                                    # try:
                                                        # showtitle = showtitle.split('. ')[1]
                                                    # except:
                                                        # pass

                                                    # if imdbnumber == 0:
                                                        # imdbnumber = self.getIMDBIDmovie(showtitle, year)

                                                    # if genre == 'Unknown':
                                                        # genre = (self.getGenre(type, showtitle, year))

                                                    # if rating == 'NR':
                                                        # rating = (self.getRating(type, showtitle, year, imdbnumber))
                                                        # rating = self.cleanRating(rating)

                                                # GenreLiveID = [genre, type, imdbnumber, dbid, Managed, 1, rating]
                                                # genre, LiveID = self.packGenreLiveID(GenreLiveID)

                                            theplot = self.CleanLabels(theplot)
                                            tmpstr += "//" + theplot + "//" + genre + "////" + (LiveID)

                                        else: #Music
                                            LiveID = 'music|0|0|False|1|NR|'
                                            artist = re.search('"artist" *: *"(.*?)"', f)
                                            
                                            if album != None and len(album.group(1)) > 0:
                                                albumTitle = album.group(1)
                                            else:
                                                albumTitle = label.group(1)
                                                
                                            if artist != None and len(artist.group(1)) > 0:
                                                artistTitle = album.group(1)
                                            else:
                                                artistTitle = ''
                                                
                                            albumTitle = self.CleanLabels(albumTitle)
                                            artistTitle = self.CleanLabels(artistTitle)
                                            
                                            tmpstr += albumTitle + "//" + artistTitle + "//" + 'Music' + "////" + LiveID
                                
                                    # file = file.replace('plugin://plugin.video.youtube/?action=play_video&videoid=', youtube_plugin)
                                    tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                                    tmpstr = tmpstr + '\n' + file.replace("\\\\", "\\")
                                    self.WriteSTRM(tmpstr, StrmType, BuildType, PluginName, DirName, LastName)  
                            else:
                                print 'PseudoLibrary - PluginWalk, filecount break'
                                self.filecount = 0
                                break
                                
            for item in dirs:
                print 'PseudoLibrary - PluginWalk, recursive directory walk'

                if self.filecount >= limit:
                    print 'PseudoLibrary - PluginWalk, recursive filecount break'
                    break

                #recursively scan all subfolders
                self.PluginWalk(item, excludeLST, limit, StrmType, BuildType, FleType, DirName, LastName)
        except:
            pass
            
        return
        

    def log(msg, level =xbmc.LOGDEBUG):
        try:
           xbmc.log(ADDON_ID + '-' + ascii(msg), level)
        except Exception,e:
            pass

            
    def uni(self, string, encoding = 'utf-8'):
        if isinstance(string, basestring):
            if not isinstance(string, unicode):
                string = unicode(string, encoding, errors='ignore')
        return string

        
    def utf(self, string):
        if isinstance(string, basestring):
            if isinstance(string, unicode):
               string = string.encode( 'utf-8', 'ignore' )
        return string


    def ascii(string):
        if isinstance(string, basestring):
            if isinstance(string, unicode):
               string = string.encode('ascii', 'ignore')
        return string
    
    
    def packGenreLiveID(self, GenreLiveID):
        print "packGenreLiveID"
        genre = GenreLiveID[0]
        GenreLiveID.pop(0)
        LiveID = (str(GenreLiveID)).replace("u'",'').replace(',','|').replace('[','').replace(']','').replace("'",'').replace(" ",'') + '|'
        return genre, LiveID
        
        
    def unpackLiveID(self, LiveID):
        print ("unpackLiveID")
        LiveID = LiveID.split('|')
        return LiveID

        
    def escapeDirJSON(self, dir_name):
        mydir = uni(dir_name)

        if (mydir.find(":")):
            mydir = mydir.replace("\\", "\\\\")
        return mydir

          
    def trim(self, content, limit, suffix):
        print "trim"
        if len(content) <= limit:
            return content
        else:
            return content[:limit].rsplit(' ', 1)[0]+suffix
           
           
    def splitall(self, path):
        print ("splitall")
        allparts = []
        while 1:
            parts = os.path.split(path)
            if parts[0] == path:  # sentinel for absolute paths
                allparts.insert(0, parts[0])
                break
            elif parts[1] == path: # sentinel for relative paths
                allparts.insert(0, parts[1])
                break
            else:
                path = parts[0]
                allparts.insert(0, parts[1])
        return allparts
    
    
    def determineWebServer(self):
        if self.discoveredWebServer:
            return

        self.discoveredWebServer = True
        self.webPort = 8080
        self.webUsername = ''
        self.webPassword = ''
        fle = xbmc.translatePath("special://profile/guisettings.xml")
        self.httpJSON = False

        try:
            dom = parse(xml)
        except Exception,e:
            print ('determineWebServer Unable to parse settings file')
            self.httpJSON = False
            return

        xml.close()
                
        try:
            plname = dom.getElementsByTagName('webserver')
            self.httpJSON = (plname[0].childNodes[0].nodeValue.lower() == 'true')
            print ('determineWebServer is ' + str(self.httpJSON))

            if self.httpJSON == True:
                plname = dom.getElementsByTagName('webserverport')
                self.webPort = int(plname[0].childNodes[0].nodeValue)
                print ('determineWebServer port ' + str(self.webPort))
                plname = dom.getElementsByTagName('webserverusername')
                self.webUsername = plname[0].childNodes[0].nodeValue
                print ('determineWebServer username ' + self.webUsername)
                plname = dom.getElementsByTagName('webserverpassword')
                self.webPassword = plname[0].childNodes[0].nodeValue
                print ('determineWebServer password is ' + self.webPassword)
        except Exception,e:
            return


    # Code for sending JSON through http adapted from code by sffjunkie (forum.xbmc.org/showthread.php?t=92196)
    def sendJSON(self, command):
        print ('sendJSON')
        data = ''
        usedhttp = False

        self.determineWebServer()
        print ('sendJSON command: ' + command)

        # If there have been problems using the server, just skip the attempt and use executejsonrpc
        if self.httpJSON == True:
            try:
                payload = command.encode('utf-8')
            except Exception,e:
                print (str(e))
                return data

            headers = {'Content-Type': 'application/json-rpc; charset=utf-8'}

            if self.webUsername != '':
                userpass = base64.encodestring('%s:%s' % (self.webUsername, self.webPassword))[:-1]
                headers['Authorization'] = 'Basic %s' % userpass

            try:
                conn = httplib.HTTPConnection('127.0.0.1', self.webPort)
                conn.request('POST', '/jsonrpc', payload, headers)
                response = conn.getresponse()

                if response.status == 200:
                    data = uni(response.read())
                    usedhttp = True

                conn.close()
            except Exception,e:
                print ("Exception when getting JSON data")

        if usedhttp == False:
            self.httpJSON = False
            
            try:
                data = xbmc.executeJSONRPC(self.uni(command))
            except UnicodeEncodeError:
                data = xbmc.executeJSONRPC(ascii(command))

        return self.uni(data)

        
    def plugin_ok(self, plugin):
        print ("plugin_ok")
        self.PluginFound = False
        self.Pluginvalid = False
        
        if plugin[0:9] == 'plugin://':
            addon = os.path.split(plugin)[0]
            addon = (plugin.split('/?')[0]).replace("plugin://","")
            addon = self.splitall(addon)[0]
            self.log("plugin id = " + addon)
        else:
            addon = plugin
            
        print 'PseudoLibrary - addon', addon        
        
        json_query = ('{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": {}, "id": 1}')
        json_folder_detail = self.sendJSON(json_query)
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
                
        for f in (file_detail):
            addonids = re.search('"addonid" *: *"(.*?)",', f)
            if addonids:
                addonid = addonids.group(1)
                if addonid.lower() == addon.lower():
                    print addonid
                    self.PluginFound = True
                    self.Pluginvalid = True
                    
        print ("PluginFound = " + str(self.PluginFound))
        
        return self.PluginFound
                
                
    def youtube_duration(self, YTID):
        print ("youtube_duration")
        url = 'https://gdata.youtube.com/feeds/api/videos/{0}?v=2'.format(YTID)
        s = urlopen(url).read()
        d = parseString(s)
        e = d.getElementsByTagName('yt:duration')[0]
        a = e.attributes['seconds']
        v = int(a.value)
        return v
        
        
    def youtube_player(self):
        print ("youtube_player")
        Plugin_1 = self.plugin_ok('plugin.video.bromix.youtube')
        Plugin_2 = self.plugin_ok('plugin.video.youtube')
        
        if Plugin_1 == True:
            path = 'plugin://plugin.video.bromix.youtube/?action=play&id='
        elif Plugin_2 == True:
            path = 'plugin://plugin.video.youtube/?action=play_video&videoid='
        else:
            path = False
            
        return path
            
            
    def playon_player(self):
        print ("playon_player")
        PlayonPath = False
        json_query = ('{"jsonrpc": "2.0", "method": "Files.GetSources", "params": {"media":"video"}, "id": 2}')
        json_folder_detail = self.sendJSON(json_query)
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in file_detail:
            labels = re.search('"label" *: *"(.*?)"', f)
            files = re.search('"file" *: *"(.*?)"', f)
            try:
                label = (labels.group(1)).lower()
                upnp = (files.group(1))
                if label == 'playon':
                    PlayonPath = upnp
                    break
            except:
                pass
        print 'PseudoLibrary - playon_player = ' + str(PlayonPath)
        return PlayonPath

        
    def getGenre(self, type, title, year):
        print ("getGenre")
        genre = 'Unknown'
        
        try:
            print ("metahander")
            self.metaget = metahandlers.MetaData(preparezip=False)
            genre = str(self.metaget.get_meta(type, title)['genre'])
            try:
                genre = str(genre.split(',')[0])
            except Exception as e:
                pass
            try:
                genre = str(genre.split(' / ')[0])
            except Exception as e:
                pass
        except Exception,e:
            pass

        if not genre or genre == 'Unknown':

            if type == 'tvshow':
                try:
                    print ("tvdb_api")
                    genre = str((self.t[title]['genre']))
                    try:
                        genre = str((genre.split('|'))[1])
                    except:
                        pass
                except Exception,e:
                    pass
            else:
                print ("tmdb")
                movieInfo = str(self.tmdbAPI.getMovie(title, year))
                try:
                    genre = str(movieInfo['genres'][0])
                    genre = str(genre.split("u'")[3]).replace("'}",'')
                except Exception,e:
                    pass

        if not genre or genre == 'None' or genre == 'Empty':
            genre = 'Unknown'
            
        return genre.replace('NA','Unknown')
        
    
    def cleanRating(self, rating):
        print ("cleanRating")
        rating = rating.replace('Rated ','').replace('US:','').replace('UK:','').replace('Unrated','NR').replace('NotRated','NR').replace('N/A','NR').replace('NA','NR').replace('Approved','NR')
        return rating
    

    def getRating(self, type, title, year, imdbid):
        print ("getRating")
        rating = 'NR'

        try:
            print ("metahander")     
            self.metaget = metahandlers.MetaData(preparezip=False)
            rating = self.metaget.get_meta(type, title)['mpaa']
        except Exception,e:
            pass
            
        rating = rating.replace('Unrated','NR').replace('NotRated','NR').replace('N/A','NR').replace('Approved','NR')
        if not rating or rating == 'NR':
        
            if type == 'tvshow':
                try:
                    print ("tvdb_api")
                    rating = str(self.t[title]['contentrating'])
                    try:
                        rating = rating.replace('|','')
                    except:
                        pass
                except Exception,e:
                    pass
            else:
                if imdbid or imdbid != 0:
                    try:
                        print ("tmdb")
                        rating = str(self.tmdbAPI.getMPAA(imdbid))
                    except Exception,e:
                        pass

        rating = rating.replace('Unrated','NR').replace('NotRated','NR').replace('N/A','NR').replace('Approved','NR')
        if not rating or rating == 'None' or rating == 'Empty':
            rating = 'NR'
            
        return (self.cleanRating(rating)).replace('M','R')


    def getTVDBID(self, title, year):
        print 'PseudoLibrary - getTVDBID'
        tvdbid = 0
        imdbid = 0
 
        try:
            print ("metahander")
            self.metaget = metahandlers.MetaData(preparezip=False)
            tvdbid = self.metaget.get_meta('tvshow', title)['tvdb_id']
        except Exception,e:
            pass

        if not tvdbid or tvdbid == 0:
            try:
                print ("tvdb_api")
                tvdbid = int(self.t[title]['id'])
            except Exception,e:
                pass

        if not tvdbid or tvdbid == 0:
            try:
                imdbid = self.getIMDBIDtv(title)
                if imdbid or imdbid != 0:
                    tvdbid = int(self.getTVDBIDbyIMDB(imdbid))
                if not tvdbid:
                    tvdbid = 0
            except Exception,e:
                pass

        if not tvdbid or tvdbid == 'None' or tvdbid == 'Empty':
            tvdbid = 0

        return tvdbid


    def getIMDBIDtv(self, title):
        print 'PseudoLibrary - getIMDBIDtv'
        imdbid = 0

        try:
            print ("metahander")
            self.metaget = metahandlers.MetaData(preparezip=False)
            imdbid = self.metaget.get_meta('tvshow', title)['imdb_id']
        except Exception,e:
            pass

        if not imdbid or imdbid == 0:
            try:
                print ("tvdb_api")
                imdbid = self.t[title]['imdb_id']
                if not imdbid:
                    imdbid = 0
            except Exception,e:
                pass

        if not imdbid or imdbid == 'None' or imdbid == 'Empty':
            imdbid = 0

        return imdbid


    def getTVDBIDbyIMDB(self, imdbid):
        print 'PseudoLibrary - getTVDBIDbyIMDB'
        tvdbid = 0

        try:
            tvdbid = self.tvdbAPI.getIdByIMDB(imdbid)
        except Exception,e:
            pass

        if not tvdbid or tvdbid == 'None' or tvdbid == 'Empty':
            tvdbid = 0
            
        return tvdbid


    def getIMDBIDmovie(self, showtitle, year):
        print 'PseudoLibrary - getIMDBIDmovie'
        imdbid = 0
        try:
            print ("metahander")
            self.metaget = metahandlers.MetaData(preparezip=False)
            imdbid = (self.metaget.get_meta('movie', showtitle)['imdb_id'])
        except Exception,e:
            pass

        if not imdbid or imdbid == 0:
            try:
                print ("tmdb")
                movieInfo = (self.tmdbAPI.getMovie(showtitle, year))
                imdbid = (movieInfo['imdb_id'])
                if not imdbid:
                    imdbid = 0
            except Exception,e:
                pass
                
        if not imdbid or imdbid == 'None' or imdbid == 'Empty':
            imdbid = 0
            
        return imdbid
        
    
    def getTVDBIDbyZap2it(self, dd_progid):
        print 'PseudoLibrary - getTVDBIDbyZap2it'
        tvdbid = 0
        
        try:
            tvdbid = self.tvdbAPI.getIdByZap2it(dd_progid)
            if not tvdbid:
                tvdbid = 0
        except Exception,e:
            pass
        
        if not tvdbid or tvdbid == 'None' or tvdbid == 'Empty':
            tvdbid = 0
            
        return tvdbid
        
        
    def getTVINFObySubtitle(self, title, subtitle):
        print 'PseudoLibrary - getTVINFObySubtitle'
        episode = ''
        episodeName = ''
        seasonNumber = 0
        episodeNumber = 0
        
        try:
            episode = self.t[title].search(subtitle, key = 'episodename')
            # Output example: [<Episode 01x01 - My First Day>]
            episode = str(episode[0])
            episode = episode.split('x')
            seasonNumber = int(episode[0].split('Episode ')[1])
            episodeNumber = int(episode[1].split(' -')[0])
            episodeName = str(episode[1]).split('- ')[1].replace('>','')
        except Exception,e:
            pass

        return episodeName, seasonNumber, episodeNumber

        
    def getTVINFObySE(self, title, seasonNumber, episodeNumber):
        print 'PseudoLibrary - getTVINFObySE'
        episode = ''
        episodeName = ''
        episodeDesc = ''
        episodeGenre = 'Unknown'
        
        try:
            episode = self.t[title][seasonNumber][episodeNumber]
            episodeName = str(episode['episodename'])
            episodeDesc = str(episode['overview'])
            episodeGenre = str(self.t[title]['genre'])
            # Output ex. Comedy|Talk Show|
            episodeGenre = str(episodeGenre)
            try:
                episodeGenre = str(episodeGenre.split('|')[1])
            except:
                pass
        except Exception,e:
            pass
        
        if episodeName != '' or episodeName != None:
            if not episodeDesc:
                episodeDesc = episodeName

        return episodeName, episodeDesc, episodeGenre
        
        
    def getMovieINFObyTitle(self, title, year):
        print 'PseudoLibrary - getMovieINFObyTitle'
        imdbid = 0
        plot = ''
        tagline = ''
        genre = 'Unknown'
        
        try:
            movieInfo = self.tmdbAPI.getMovie((title), year)
            imdbid = movieInfo['imdb_id']
            try:
                plot = str(movieInfo['overview'])
            except:
                pass
            try:
                tagline = str(movieInfo['tagline'])
            except:
                pass
            try:
                genre = str(movieInfo['genres'][0])
                genre = str((genre.split("u'")[3])).replace("'}",'')
            except:
                pass
                
            if not imdbid or imdbid == 'None' or imdbid == 'Empty':
                imdbid = 0
                
        except Exception,e:
            pass

        return imdbid, plot, tagline, genre


    def OpenURL(self, url):
        print "OpenURL"
        try:
            f = urllib2.urlopen(url)
            data = f.readlines()
            f.close()
            return data
        except urllib2.URLError as e:
            pass
        
    def createYoutubeFilelist(self, StrmType, BuildType, setting1, setting2, setting3, setting4, FolderName):
        print ("createYoutubeFilelist")
        showList = []
        showcount = 0
        stop = 0
        LiveID = 'tvshow|0|0|False|1|NR|'
        youtube_plugin = self.youtube_player()
        limit = int(setting3)
        
        if youtube_plugin != False:
            print "createYoutubeFilelist, youtube_plugin true"
            
            if setting4 == '1':
                stop = (limit / 25)
                YTMSG = 'Channel'
            elif setting4 == '2':
                stop = (limit / 25)
                YTMSG = 'Playlist'
            elif setting4 == '3':
                YTMSG = 'MultiTube'
                self.BuildMultiYoutubeChannelNetwork(StrmType, BuildType, setting1, setting2, setting3, setting4, FolderName)            
            startIndex = 1
            
            for x in range(stop):
                if setting4 == '1': #youtube user uploads
                    youtubechannel = 'http://gdata.youtube.com/feeds/api/users/' +setting1+ '/uploads?start-index=' +str(startIndex)+ '&max-results=25'
                    youtube = youtubechannel
                elif setting4 == '2': #youtube playlist 
                    youtubeplaylist = 'https://gdata.youtube.com/feeds/api/playlists/' +setting1+ '?start-index=' +str(startIndex)
                    youtube = youtubeplaylist                        
                elif setting4 == '4': #youtube new subscriptions
                    youtubesubscript = 'http://gdata.youtube.com/feeds/api/users/' +setting1+ '/newsubscriptionvideos?start-index=' +str(startIndex)+ '&max-results=25'
                    youtube = youtubesubscript                  
                elif setting4 == '5': #youtube favorites
                    youtubefavorites = 'https://gdata.youtube.com/feeds/api/users/' +setting1+ '/favorites?start-index=' +str(startIndex)+ '&max-results=25'
                    youtube = youtubefavorites      
                    
                feed = feedparser.parse(youtube) 
                print ("createYoutubeFilelist, " + YTMSG + " " + setting1)  
                print ('createYoutubeFilelist, youtube = ' + str(youtube))                
                startIndex = startIndex + 25
                    
                for i in range(len(feed['entries'])):
                    # self.updateDialogProgress = i * 1 // self.updateDialogProgressCount
                    try:
                        showtitle = feed.channel.author_detail['name']
                        showtitle = showtitle.replace(":", "").replace('YouTube', setting1)

                        try:
                            genre = (feed.entries[0].tags[1]['term'])
                        except Exception,e:
                            print ("createYoutubeFilelist, Invalid genre")
                            genre = 'Youtube'
                        
                        try:
                            thumburl = feed.entries[i].media_thumbnail[0]['url']
                        except Exception,e:
                            print ("createYoutubeFilelist, Invalid media_thumbnail")
                            pass 
                        
                        try:
                            print ("createYoutubeFilelist, feed parsing")
                            #Time when the episode was published
                            time = (feed.entries[i].published_parsed)
                            time = str(time)
                            time = time.replace("time.struct_time", "")            
                            
                            #Some channels release more than one episode daily.  This section converts the mm/dd/hh to season=mm episode=dd+hh
                            showseason = [word for word in time.split() if word.startswith('tm_mon=')]
                            showseason = str(showseason)
                            showseason = showseason.replace("['tm_mon=", "")
                            showseason = showseason.replace(",']", "")
                            showepisodenum = [word for word in time.split() if word.startswith('tm_mday=')]
                            showepisodenum = str(showepisodenum)
                            showepisodenum = showepisodenum.replace("['tm_mday=", "")
                            showepisodenum = showepisodenum.replace(",']", "")
                            showepisodenuma = [word for word in time.split() if word.startswith('tm_hour=')]
                            showepisodenuma = str(showepisodenuma)
                            showepisodenuma = showepisodenuma.replace("['tm_hour=", "")
                            showepisodenuma = showepisodenuma.replace(",']", "")
                            
                            print "createYoutubeFilelist", showseason, showepisodenum, showepisodenuma
                        except Exception,e:
                            print ("createYoutubeFilelist, feed parsing Error")
                            pass
                    
                        try:
                            eptitle = feed.entries[i].title
                            eptitle = re.sub('[!@#$/:]', '', eptitle)
                            eptitle = re.sub("[\W]+", " ", eptitle.strip()) 
                        except Exception,e:
                            eptitle = setting1
                            eptitle = eptitle.replace('+',', ')
                        try:
                            showtitle = (self.trim(showtitle, 350, ''))
                        except Exception,e:
                            print ("showtitle Trim failed" + str(e))
                            showtitle = (showtitle[:350])
                            pass
                        showtitle = showtitle.replace('/','')
                        
                        try:
                            eptitle = (self.trim(eptitle, 350, ''))
                        except Exception,e:
                            print ("eptitle Trim failed" + str(e))
                            eptitle = (eptitle[:350])  
                        
                        
                        try:
                            summary = feed.entries[i].summary
                            summary = (summary)
                            summary = re.sub("[\W]+", " ", summary.strip())                       
                        except Exception,e:
                            summary = showtitle +' - '+ eptitle
                        print "summary", summary
                        
                        try:
                            summary = (self.trim(summary, 350, '...'))
                        except Exception,e:
                            print ("summary Trim failed" + str(e))
                            summary = (summary[:350])

                        #remove // because interferes with playlist split.
                        summary = self.CleanLabels(summary)
                        
                        try:
                            runtime = feed.entries[i].yt_duration['seconds']
                            print ('createYoutubeFilelist, runtime = ' + str(runtime))
                            runtime = int(runtime)
                            # runtime = round(runtime/60.0)
                            # runtime = int(runtime)
                        except Exception,e:
                            runtime = 0

                        
                        if runtime >= 1:
                            duration = runtime
                        else:
                            duration = 90
                            print ("createYoutubeFilelist, duration error defaulted to 90 min")
                        
                        if self.background == False:
                            self.updateDialog.update(self.updateDialogProgress, "Parsing" + ": " + BuildType, str(YTMSG) + ' ' + showtitle, "added " + str(showcount) + " entries")
                            
                        # duration = round(duration*60.0)
                        print ('createYoutubeFilelist, duration = ' + str(duration))
                        duration = int(duration)
                        url = feed.entries[i].media_player['url']
                        url = url.replace("https://", "").replace("http://", "").replace("www.youtube.com/watch?v=", "").replace("&feature=youtube_gdata_player", "").replace("?version=3&f=playlists&app=youtube_gdata", "").replace("?version=3&f=newsubscriptionvideos&app=youtube_gdata", "")
                        
                        # Build M3U
                        istvshow = True
                        tmpstr = str(duration) + ',' + showtitle + '//' + eptitle + "//" + summary + "//" + genre + "////" + LiveID + '\n' + youtube_plugin + url
                        tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                        self.WriteSTRM(tmpstr, StrmType, BuildType, YTMSG, FolderName, showtitle)  
                        showcount += 1
                    
                    except Exception,e:
                        pass

    
    def BuildMultiYoutubeChannelNetwork(self, StrmType, BuildType, setting1, setting2, setting3, setting4, FolderName):
        print ("BuildMultiYoutubeChannelNetwork")
        channelList = setting1.split(',')
        tmpstr = ''
        showList = []
        
        for n in range(len(channelList)):
            self.createYoutubeFilelist(StrmType, BuildType, channelList[n], '1', setting3, '1', FolderName)   

            
    def CleanLabels(self, label):
        print 'PseudoLibrary - CleanLabels'
        label = label.replace('[B]','').replace('[/B]','').replace('[/COLOR]','').replace('[COLOR=blue]','').replace('[COLOR=cyan]','').replace('[COLOR=red]','').replace('[COLOR=green]','').replace('[COLOR=yellow]','').replace(' [HD]', '').replace('(Sub) ','').replace('(Dub) ','').replace(' [cc]','').replace('\\',' ')
        return label
        
    
    def WriteSTRM(self, tmpstr, StrmType, BuildType, PluginName, DirName, LastName):
        print 'PseudoLibrary - WriteSTRM'
        WriteNFO = False
        STRM_LOC = REAL_SETTINGS.getSetting('STRM_LOC')
        WriteNFO = REAL_SETTINGS.getSetting("Write_NFOS") == "true"
        tmpstrLST = tmpstr.split('\n')[0]

        file = tmpstr.split('\n')[1]
        tmpstr = tmpstrLST.split('//')
        dur = tmpstr[0].split(',')[0]
        title = tmpstr[0].split(',')[1]
        eptitle = tmpstr[1]
        description = tmpstr[2]
        genre = tmpstr[3]
        GenreLiveID = tmpstr[5]
        liveID = self.unpackLiveID(GenreLiveID)
        DirName = re.sub('[\/:*?<>|!@#$/:]', '', DirName)
        LastName = re.sub('[\/:*?<>|!@#$/:]', '', LastName)
        # print dur, title, eptitle, description, genre, GenreLiveID, liveID

        if StrmType.lower() == 'tvshow' or StrmType.lower() == 'tvshows' or StrmType.lower() == 'tv':
            StrmType = 'TVShows'
            FleName = (title + ' - ' + eptitle + '.strm').replace(":"," - ")
            FleName = re.sub('[\/:*?<>|!@#$/:]', '', FleName)
            title = re.sub('[\/:*?<>|!@#$/:]', '', title)
            Folder = os.path.join(STRM_LOC,StrmType)
            
            if DirName == '':
                FleFolder = os.path.join(Folder,title)
            else:
                FleFolder = os.path.join(Folder,DirName)
            
            # FleName = "".join(i for i in FleName if i not in "\/:*?<>|")
            
        elif StrmType.lower() == 'episode' or StrmType.lower() == 'episodes':
            StrmType = 'TVShows'
            FleName = (title + ' - ' + eptitle + '.strm').replace(":"," - ")
            FleName = re.sub('[\/:*?<>|!@#$/:]', '', FleName)
            Folder = os.path.join(STRM_LOC,StrmType)
            
            if DirName == '':
                FleFolder = os.path.join(Folder,LastName)
            else:
                FleFolder = os.path.join(Folder,DirName)

        elif StrmType.lower() == 'movie' or StrmType.lower() == 'movies':
            StrmType = 'Movies'
            FleName = (title + '.strm').replace(":"," - ")
            FleName = re.sub('[\/:*?<>|!@#$/:]', '', FleName)
            title = re.sub('[\/:*?<>|!@#$/:]', '', title)
            Folder = os.path.join(STRM_LOC,StrmType)
            
            if DirName == '':
                FleFolder = os.path.join(Folder,title)
            else:
                FleFolder = os.path.join(Folder,DirName)
                
        elif StrmType.lower() == 'music video' or StrmType.lower() == 'music videos' or StrmType.lower() == 'music':
            StrmType = 'Music'
            FleName = (title + '.strm').replace(":"," - ")
            FleName = re.sub('[\/:*?<>|!@#$/:]', '', FleName)
            title = re.sub('[\/:*?<>|!@#$/:]', '', title)
            Folder = os.path.join(STRM_LOC,StrmType)
            
            if DirName == '':
                FleFolder = os.path.join(Folder)
            else:
                FleFolder = os.path.join(Folder,DirName)

        else:
            StrmType = 'Generic'
            
            if BuildType.lower() == 'youtube':
                if REAL_SETTINGS.getSetting('Youtube_Sort') == 'true':
                    FleName = (title + ' - ' + eptitle + '.strm').replace(":"," - ")
                    FleName = re.sub('[\/:*?<>|!@#$/:]', '', FleName)
                    Folder = os.path.join(STRM_LOC,BuildType)
                    
                    if DirName == '':
                        FleFolder = os.path.join(Folder,PluginName,LastName)
                    else:
                        FleFolder = os.path.join(Folder,PluginName,DirName)
                else:
                    FleName = (title + ' - ' + eptitle + '.strm').replace(":"," - ")
                    FleName = re.sub('[\/:*?<>|!@#$/:]', '', FleName)
                    Folder = os.path.join(STRM_LOC,StrmType)
                    
                    if DirName == '':
                        FleFolder = os.path.join(Folder,BuildType,LastName)
                    else:
                        FleFolder = os.path.join(Folder,BuildType,DirName) 
            else:
                FleName = (title + ' - ' + eptitle + '.strm').replace(":"," - ")
                FleName = re.sub('[\/:*?<>|!@#$/:]', '', FleName)
                Folder = os.path.join(STRM_LOC,StrmType)
                
                if DirName == '':
                    FleFolder = os.path.join(Folder,PluginName,LastName)
                else:
                    FleFolder = os.path.join(Folder,PluginName,DirName)
                            
        Fle = (os.path.join(FleFolder,FleName))
        print 'PseudoLibrary - WriteSTRM - ' + Fle

        try:
            id = liveID[1]
        except:
            pass
        
        if not xbmcvfs.exists(FleFolder):
            xbmcvfs.delete(FleFolder)
            xbmcvfs.mkdirs(FleFolder)

        if xbmcvfs.exists(Fle):
            try:
                xbmcvfs.delete(Fle)
            except:
                pass
        try:
            f = FileAccess.open(Fle, "w")
            f.write("%s\n" % file)
            f.close
        except:
            pass

        #todo
        #WriteNFO
        #trigger xbmc library scan
        #auto add folders as xbmc source
        #source list switch for donors
        
            