#   Copyright (C) 2013 Jason Anderson, Lunatixz
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


import xbmc
import os, shutil
import codecs
import xbmcvfs
import xbmcaddon
VFS_AVAILABLE = True

__addon__     = xbmcaddon.Addon(id='script.pseudo.library')
__addonid__   = __addon__.getAddonInfo('id')


def ascii(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode):
           string = string.encode('ascii', 'ignore')

    return string

class FileAccess:
    @staticmethod
    def log(txt):
        if __addon__.getSetting( "logEnabled" ) == "true":
            if isinstance (txt,str):
                txt = txt.decode("utf-8")
            message = u'%s: %s' % (__addonid__, txt)
            xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)


    @staticmethod
    def open(filename, mode, encoding = "utf-8"):
        fle = 0
        FileAccess.log("trying to open " + filename)
        
        try:
            return VFSFile(filename, mode)
        except UnicodeDecodeError:
            return FileAccess.open(ascii(filename), mode, encoding)

        return fle


    @staticmethod
    def copy(orgfilename, newfilename):
        FileAccess.log('copying ' + orgfilename + ' to ' + newfilename)
        xbmcvfs.copy(orgfilename, newfilename)
        return True


    @staticmethod
    def exists(filename):
        try:
            return xbmcvfs.exists(filename)
        except UnicodeDecodeError:
            return FileAccess.exists(ascii(filename))

        return False


    @staticmethod
    def openSMB(filename, mode, encoding = "utf-8"):
        fle = 0

        if os.name.lower() == 'nt':
            newname = '\\\\' + filename[6:]

            try:
                fle = codecs.open(newname, mode, encoding)
            except:
                fle = 0

        return fle


    @staticmethod
    def existsSMB(filename):
        if os.name.lower() == 'nt':
            filename = '\\\\' + filename[6:]
            return FileAccess.exists(filename)

        return False


    @staticmethod
    def rename(path, newpath):
        FileAccess.log("rename " + path + " to " + newpath)

        try:
            if xbmcvfs.rename(path, newpath):
                return True
        except:
            pass

        if path[0:6].lower() == 'smb://' or newpath[0:6].lower() == 'smb://':
            if os.name.lower() == 'nt':
                FileAccess.log("Modifying name")
                if path[0:6].lower() == 'smb://':
                    path = '\\\\' + path[6:]

                if newpath[0:6].lower() == 'smb://':
                    newpath = '\\\\' + newpath[6:]

        try:
            os.rename(path, newpath)
            FileAccess.log("os.rename")
            return True
        except:
            pass

        try:
            shutil.move(path, newpath)
            FileAccess.log("shutil.move")
            return True
        except:
            pass

        FileAccess.log("OSError")
        raise OSError()


    @staticmethod
    def makedirs(directory):
        try:
            os.makedirs(directory)
        except:
            FileAccess._makedirs(directory)


    @staticmethod
    def _makedirs(path):
        if len(path) == 0:
            return False

        if(xbmcvfs.exists(path)):
            return True

        success = xbmcvfs.mkdir(path)

        if success == False:
            if path == os.path.dirname(path):
                return False

            if FileAccess._makedirs(os.path.dirname(path)):
                return xbmcvfs.mkdir(path)

        return xbmcvfs.exists(path)



class VFSFile:
    def __init__(self, filename, mode):
        # log("VFSFile: trying to open " + filename)

        if mode == 'w':
            self.currentFile = xbmcvfs.File(filename, 'wb')
        else:        
            self.currentFile = xbmcvfs.File(filename)

        # log("VFSFile: Opening " + filename, xbmc.LOGDEBUG)
        
        if self.currentFile == None:
            log("VFSFile: Couldnt open " + filename, xbmc.LOGERROR)


    def read(self, bytes):
        return self.currentFile.read(bytes)
        
        
    def write(self, data):
        if isinstance(data, unicode):
            data = bytearray(data, "utf-8")
            data = bytes(data)
    
        return self.currentFile.write(data)
        
        
    def close(self):
        return self.currentFile.close()
        
        
    def seek(self, bytes, offset):
        return self.currentFile.seek(bytes, offset)
        
        
    def size(self):
        loc = self.currentFile.size()
        return loc
        
        
    def readlines(self):
        return self.currentFile.read().split('\n')    
        
    def writelines(self):
        return self.currentFile.write().split('\n')
        
        
    def tell(self):
        loc = self.currentFile.seek(0, 1)
        return loc
        

