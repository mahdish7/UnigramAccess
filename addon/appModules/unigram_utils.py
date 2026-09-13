# -*- coding:utf-8 -*-
# UnigramAccess: Shared utility functions and constants.

import ctypes
import os

from controlTypes import Role
from keyboardHandler import KeyboardInputGesture
import mouseHandler
from winBindings import user32 as winUser

import time

from .cnf import conf
from .data import active_download_keywords, context_menu_items, icons_from_context_menu


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


def get_context_menu_targets(action):
	"""Retrieve target matching labels and icons for a context menu action in the active interface language."""
	entry = context_menu_items.get(action, {})
	labels = entry.get(conf.get("lang"), ())
	targets = set(labels)

	icon = icons_from_context_menu.get(action)
	if icon:
		targets.add(icon)

	if action == "pin":
		attach_icon = icons_from_context_menu.get("attach")
		unpin_icon = icons_from_context_menu.get("unpin")
		if attach_icon:
			targets.add(attach_icon)
		if unpin_icon:
			targets.add(unpin_icon)
	elif action == "read":
		unread_icon = icons_from_context_menu.get("unread")
		if unread_icon:
			targets.add(unread_icon)

	return targets


def find_and_activate_context_menu_item(obj, target, close_on_failure=True):
	"""Find and invoke a menu item matching target from the context menu containing obj.

	Safely skips separators and items without children. Resolves action names
	via context_menu_items or accepts an iterable/string of explicit targets.

	@param obj: The focused menu item or menu container.
	@param target: An action key (e.g. 'select', 'delete') or iterable/string of target labels.
	@param close_on_failure: Whether to send Escape if the target is not found.
	@return: True if target was found and invoked, False otherwise.
	"""
	if not obj:
		return False

	container = obj if getattr(obj, "role", None) in (Role.MENU, Role.POPUPMENU) else getattr(obj, "parent", None)
	if not container or not getattr(container, "children", None):
		if close_on_failure:
			CACHED_KEYS["escape"].send()
		return False

	targets = get_context_menu_targets(target) if isinstance(target, str) and target in context_menu_items else target
	if isinstance(targets, str):
		targets = (targets,)
	target_set = {t.lower() for t in targets if t}

	for item in getattr(container, "children", []):
		if getattr(item, "role", None) != Role.MENUITEM:
			continue

		item_name = getattr(item, "name", None) or ""
		first_child = getattr(item, "firstChild", None)
		first_name = getattr(first_child, "name", None) or ""

		if (item_name and item_name.lower() in target_set) or (first_name and first_name.lower() in target_set):
			item.doAction()
			return True

	if close_on_failure:
		CACHED_KEYS["escape"].send()
	return False

