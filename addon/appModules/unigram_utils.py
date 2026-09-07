# -*- coding:utf-8 -*-
# UnigramAccess: Shared utility functions and constants.

import ctypes
import os

from keyboardHandler import KeyboardInputGesture
import mouseHandler
from winBindings import user32 as winUser

from .data import active_download_keywords


# Path to the media assets directory (WAV files for audio cues).
BASE_DIR = os.path.join(os.path.dirname(__file__), "media")

# Pre-cached KeyboardInputGesture objects for frequently simulated key presses.
CACHED_KEYS = {
	"upArrow": KeyboardInputGesture.fromName("upArrow"),
	"downArrow": KeyboardInputGesture.fromName("downArrow"),
	"fixed_downArrow": KeyboardInputGesture.fromName("shift+downArrow"),
	"Applications": KeyboardInputGesture.fromName("Applications"),
	"escape": KeyboardInputGesture.fromName("escape"),
	"space": KeyboardInputGesture.fromName("space"),
}


def fixedDoAction(obj):
	"""Perform a physical left-click on the center of an element.

	Some UWP buttons do not respond to UIA invoke/doAction.
	This workaround moves the cursor, clicks, then restores the cursor position.
	"""
	p = obj.location.center
	point = ctypes.wintypes.POINT()
	winUser.dll.GetCursorPos(ctypes.byref(point))
	winUser.dll.SetCursorPos(p.x, p.y)
	mouseHandler.executeMouseEvent(winUser.MOUSEEVENTF.LEFTDOWN, 0, 0)
	mouseHandler.executeMouseEvent(winUser.MOUSEEVENTF.LEFTUP, 0, 0)
	winUser.dll.SetCursorPos(point.x, point.y)


def isActivelyDownloading(name):
	"""Check if an element label indicates an actively downloading media button."""
	if not name:
		return False
	base_name = name.split(": ")[0] if ": " in name else name
	base_name_lower = base_name.lower()
	return any(kw in base_name_lower for kw_list in active_download_keywords.values() for kw in kw_list)

