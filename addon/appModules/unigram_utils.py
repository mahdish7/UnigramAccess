# -*- coding:utf-8 -*-
# UnigramAccess: Shared utility functions and constants.

import ctypes
import os
import time

from controlTypes import Role, State
from keyboardHandler import KeyboardInputGesture
import mouseHandler
from winBindings import user32 as winUser
import api
import core
import speech
import ui

from .cnf import conf
from .data import active_download_keywords, context_menu_items, icons_from_context_menu
from .unigram_logger import ulog as log


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
	kws = active_download_keywords.get(conf.get("lang"), ())
	return any(kw in base_name_lower for kw in kws)


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


class FocusManager:
	"""Unified focus tracking, safe restoration, and speech suppression for Unigram."""

	def __init__(self, appModule):
		self.appModule = appModule
		self._saved = {}
		self._hold_target = None
		self._cancel_condition = None
		self._hold_timer = None
		self._timer_token = None
		self._on_restore = None
		self._announce = False
		self._notification = None

	def hold(self, obj=None, cancel_condition=None, delay_ms=0, on_restore=None, announce=False, notification=None):
		"""Hold focus on obj (or current focus). If an action moves focus away, it will be restored.

		Args:
			obj: Target object to hold focus on. Defaults to current focus.
			cancel_condition: Optional callable(focus_obj) -> bool. If True, hold restoration is aborted.
			delay_ms: If 0 (default), event-driven restoration on focus change.
			          If > 0, defers restoration by delay_ms, suppressing interim focus changes.
			on_restore: Optional callable(restored_obj) invoked upon successful restoration.
			announce: If False (default), restores silently. If True, the restored target is announced by NVDA.
			notification: Optional speech message to deliver once focus is safely settled.
		"""
		self.release()
		if obj is None:
			obj = api.getFocusObject()
		self._hold_target = obj
		self._cancel_condition = cancel_condition
		self._on_restore = on_restore
		self._announce = announce
		self._notification = notification

		if delay_ms > 0:
			token = object()
			self._timer_token = token

			def _on_timer():
				if self._timer_token is not token:
					return
				self._timer_token = None
				self._hold_timer = None

				target = self._hold_target
				self._hold_target = None

				if not target:
					return

				current = api.getFocusObject()
				if self._is_cancelled(current):
					log.debug("FocusManager: hold cancelled by cancel_condition")
					return

				if current == target:
					notif = self._notification
					self._notification = None
					if notif:
						ui.message(notif)
					return

				log.debug("FocusManager: timer expired; restoring focus to target")
				if not self._announce:
					speech.cancelSpeech()
				self.safe_set_focus(target)

			self._hold_timer = core.callLater(delay_ms, _on_timer)

		return obj

	def execute_action(self, action, target=None, notification=None, cancel_condition=None, on_restore=None, announce=False):
		"""Phase 1: Execute action, saving initial target and notification for event-driven restoration (no timers)."""
		if target is None:
			target = api.getFocusObject()
		self.hold(obj=target, cancel_condition=cancel_condition, delay_ms=0, on_restore=on_restore, announce=announce, notification=notification)
		try:
			action()
		except Exception as e:
			self.release()
			log.debugException(f"FocusManager.execute_action failed: {e}")
			return False
		return True

	def release(self):
		"""Release any held focus, allowing focus to move freely without restoration."""
		self._timer_token = None
		if self._hold_timer:
			try:
				self._hold_timer.Stop()
			except Exception:
				pass
			self._hold_timer = None
		self._hold_target = None
		self._cancel_condition = None
		self._on_restore = None
		self._announce = False
		self._notification = None

	def safe_set_focus(self, candidate):
		"""Safely set focus to candidate if alive and focusable."""
		if not candidate:
			return False
		try:
			if not getattr(candidate, "parent", None):
				return False
			if getattr(candidate, "isFocusable", True):
				candidate.setFocus()
				return True
		except Exception:
			pass
		return False

	def save(self, key, obj=None):
		"""Save a focus target under key. Defaults to current focus object if obj is None."""
		if obj is None:
			obj = api.getFocusObject()
		if obj:
			self._saved[key] = obj
		return obj

	def get(self, key):
		"""Retrieve a saved focus target by key."""
		return self._saved.get(key)

	def discard(self, key):
		"""Discard a saved focus target."""
		self._saved.pop(key, None)

	def _is_cancelled(self, obj):
		"""Evaluate if cancel_condition is satisfied."""
		if not callable(self._cancel_condition):
			return False
		try:
			return bool(self._cancel_condition(obj))
		except TypeError:
			try:
				return bool(self._cancel_condition())
			except Exception:
				return False
		except Exception:
			return False

	def handle_focus_change(self, obj):
		"""Process focus changes in event_gainFocus.

		Returns True if the event was consumed and should not be processed further.
		"""
		if not self._hold_target:
			return False

		target = self._hold_target

		# Check if dynamic cancel condition is met
		if self._is_cancelled(obj):
			log.debug("FocusManager: cancel condition satisfied; releasing hold")
			self.release()
			return False

		# If an explicit deferred timer (delay_ms > 0) is running:
		if self._timer_token is not None:
			# Intermediate focus change away from target: silence it and consume
			if obj != target:
				speech.cancelSpeech()
				return True
			return False

		# Phase 3: Work finished and focus has returned to the initial target
		if obj == target:
			if not self._announce:
				speech.cancelSpeech()
			notif = self._notification
			on_restore = self._on_restore
			self.release()
			if callable(on_restore):
				try:
					on_restore(obj)
				except Exception:
					pass
			if notif:
				ui.message(notif)
			return not self._announce

		# Phase 2: In-flight intermediate focus movement away from target
		# Keep completely silent and redirect focus back to target
		speech.cancelSpeech()
		if not self.safe_set_focus(target):
			# If target can no longer be focused (destroyed or detached)
			notif = self._notification
			self.release()
			if notif:
				ui.message(notif)
			return False

		return True


