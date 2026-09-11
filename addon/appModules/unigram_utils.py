# -*- coding:utf-8 -*-
# UnigramAccess: Shared utility functions and constants.

import ctypes
import os

from keyboardHandler import KeyboardInputGesture
import mouseHandler
from winBindings import user32 as winUser

import time

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


def clickElementWithMouse(obj):
	"""Perform a physical mouse click on an element using standard UIA clickable coordinates.

	Moves the cursor to the element's clickable point, executes the primary click,
	and restores the cursor to its original position.
	"""
	res = obj.UIAElement.GetClickablePoint()
	if isinstance(res, tuple):
		pt, got_clickable = res
		if not got_clickable:
			return False
	else:
		pt = res

	orig_pos = ctypes.wintypes.POINT()
	winUser.dll.GetCursorPos(ctypes.byref(orig_pos))

	try:
		winUser.dll.SetCursorPos(pt.x, pt.y)
		time.sleep(0.015)
		mouseHandler.doPrimaryClick()
		time.sleep(0.015)
		return True
	finally:
		winUser.dll.SetCursorPos(orig_pos.x, orig_pos.y)


def isActivelyDownloading(name):
	"""Check if an element label indicates an actively downloading media button."""
	if not name:
		return False
	base_name = name.split(": ")[0] if ": " in name else name
	base_name_lower = base_name.lower()
	return any(kw in base_name_lower for kw_list in active_download_keywords.values() for kw in kw_list)

