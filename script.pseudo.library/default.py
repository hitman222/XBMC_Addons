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
import os
from library import *
library = library()

if dlg.yesno("PseudoLibrary", "Generate Strm's ?"):
    SETTINGS_LOC = REAL_SETTINGS.getAddonInfo('profile')
    if REAL_SETTINGS.getSetting('SanityCheck') == 'false':
        library.readSettings(SETTINGS_LOC, False)
        REAL_SETTINGS.setSetting("SanityCheck","false")