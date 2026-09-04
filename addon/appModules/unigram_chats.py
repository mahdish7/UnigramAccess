# -*- coding:utf-8 -*-
# UnigramAccess: Chat list interaction logic (delete chat, leave group/channel, remove bot, etc.).

import os

import api
from controlTypes import Role, State
from nvwave import playWaveFile
import speech
from ui import message

import addonHandler

addonHandler.initTranslation()

from .cnf import conf
from .data import (
	chat_deletion_keywords,
	icons_from_context_menu,
)
from .unigram_formatting import formatChatElementOnFocus
from .unigram_logger import ulog as log
from .unigram_utils import BASE_DIR, CACHED_KEYS


class UnigramChats:
	"""Handles chat-level interactions and deletion in Unigram."""

	def __init__(self, appModule):
		self.appModule = appModule

	def is_chat_item(self, obj):
		"""Check whether an NVDAObject is an item in the chats list."""
		try:
			if not obj:
				return False
			curr = obj
			if curr.role != Role.LISTITEM and getattr(curr, "parent", None) and curr.parent.role == Role.LISTITEM:
				curr = curr.parent
			if curr.role == Role.LISTITEM:
				parent = getattr(curr, "parent", None)
				return getattr(parent, "UIAAutomationId", "") == "ChatsList"
			return False
		except Exception:
			return False

	def _get_adjacent_item(self, item, forward=True):
		"""Find the nearest adjacent valid chat item."""
		curr = item
		depth = 0
		while curr and depth < 6:
			curr = getattr(curr, "next" if forward else "previous", None)
			depth += 1
			if not curr:
				break
			if getattr(curr, "role", None) == Role.LISTITEM and self.is_chat_item(curr):
				return curr
		return None

	def _safe_set_focus(self, candidate):
		"""Safely set focus to candidate or its focusable child."""
		if not candidate:
			return False
		try:
			if not getattr(candidate, "parent", None):
				return False
			loc = getattr(candidate, "location", None)
			if not loc or not loc.width or not loc.height:
				return False
			# First attempt: direct setFocus
			try:
				candidate.setFocus()
				return True
			except Exception:
				pass
			# Second attempt: firstChild if available
			first = getattr(candidate, "firstChild", None)
			if first and getattr(first, "location", None) and first.location.width:
				first.setFocus()
				return True
		except Exception:
			pass
		return False

	def restore_deletion_focus(self):
		"""Restore focus prioritizing initial_obj, then next_obj, then prev_obj.

		If cancellation occurred, initial_obj is still valid and focused (first condition).
		If deletion occurred, initial_obj is invalid and fails, falling through to
		next_obj (second condition) or prev_obj (third condition).

		Returns:
			str: 'initial', 'next', 'previous', or 'fallback' depending on which candidate was focused,
			or False if no candidate could be focused.
		"""
		if not isinstance(self.appModule.isDelete, dict):
			return False

		candidates = [
			("initial", self.appModule.isDelete.get("initial_obj")),
			("next", self.appModule.isDelete.get("next_obj")),
			("previous", self.appModule.isDelete.get("prev_obj")),
		]

		log.debug("Attempting chat focus restoration")
		for name, candidate in candidates:
			if not candidate:
				continue
			if self._safe_set_focus(candidate):
				log.debug(f"Successfully restored focus to {name} chat candidate (role={getattr(candidate, 'role', None)})")
				return name

		log.debug("No valid chat candidate could be focused; attempting fallback to chat list.")
		try:
			self.appModule.nav_helper.script_toChatList(False)
			return "fallback"
		except Exception:
			pass
		return False

	def start_delete_chat(self, isCompleteDeletion=False):
		"""Begin the multi-step chat deletion / leave flow.

		Saves the initial object, next item, and previous item for focus restoration,
		then opens the context menu to find the delete option.
		"""
		obj = api.getFocusObject()
		if not self.is_chat_item(obj):
			return False

		curr_item = obj
		if getattr(curr_item, "parent", None) and curr_item.parent.role == Role.LISTITEM:
			curr_item = curr_item.parent

		next_obj = self._get_adjacent_item(curr_item, forward=True)
		prev_obj = self._get_adjacent_item(curr_item, forward=False)

		self.appModule.isDelete = {
			"target": "chats",
			"isCompleteDeletion": isCompleteDeletion,
			"initial_obj": curr_item,
			"next_obj": next_obj,
			"prev_obj": prev_obj,
			"message": _("Chat deleted on both sides") if isCompleteDeletion else _("Chat deleted"),
			"state": 0,
		}
		if conf.get("audioPlaybackWhenDeleted"):
			self.appModule.isDelete["message"] = "audio"

		CACHED_KEYS["Applications"].send()
		return True

	def _resolve_dialog_elements(self, obj):
		"""Resolve the checkbox, primary button, and secondary button from the focused object or its container."""
		checkbox = None
		primary_btn = None
		secondary_btn = None

		def check_candidate(item):
			nonlocal checkbox, primary_btn, secondary_btn
			if not item:
				return
			try:
				auto_id = getattr(item, "UIAAutomationId", "") or ""
				role = getattr(item, "role", None)

				if not checkbox and (auto_id in ("CheckBox", "RevokeCheck") or role == Role.CHECKBOX):
					checkbox = item
				elif not primary_btn and auto_id == "PrimaryButton":
					primary_btn = item
				elif not secondary_btn and auto_id == "SecondaryButton":
					secondary_btn = item
			except Exception:
				pass

		# 1. Check focused object itself first
		check_candidate(obj)

		# 2. Check direct siblings
		try:
			check_candidate(getattr(obj, "next", None))
			check_candidate(getattr(obj, "previous", None))
		except Exception:
			pass

		# 3. Find the dialog container (walk up to Role.DIALOG or at most 4 levels)
		dialog = None
		curr = obj
		depth = 0
		while curr and depth < 4:
			if getattr(curr, "role", None) == Role.DIALOG:
				dialog = curr
				break
			curr = getattr(curr, "parent", None)
			depth += 1

		container = dialog or getattr(obj, "parent", None)

		if container:
			try:
				for child in getattr(container, "children", []):
					check_candidate(child)
					# If child is a pane (e.g. ScrollingHost), also inspect its direct children
					if getattr(child, "role", None) == Role.PANE:
						for subchild in getattr(child, "children", []):
							check_candidate(subchild)
					if checkbox and primary_btn and secondary_btn:
						break
			except Exception:
				pass

		# 4. Fallback: if primary_btn or secondary_btn is still not found, search upward ancestors
		if not primary_btn or not secondary_btn:
			curr = getattr(obj, "parent", None)
			depth = 0
			while curr and depth < 3:
				try:
					for child in getattr(curr, "children", []):
						check_candidate(child)
						if primary_btn and secondary_btn:
							break
				except Exception:
					pass
				if primary_btn and secondary_btn:
					break
				curr = getattr(curr, "parent", None)
				depth += 1

		return checkbox, primary_btn, secondary_btn

	def handle_deletion_step(self, obj):
		"""Execute the next step in the chat deletion state machine.

		State 0: Find and click delete in context menu.
		State 1: Handle confirmation dialog (CheckBox + PrimaryButton).
		State "awaiting_confirmation": Track dialog interaction and restore focus on close.
		State 2+: Announce result and restore focus.
		"""
		if not conf.get("confirmation_at_deletion"):
			speech.cancelSpeech()

		state = self.appModule.isDelete.get("state", 0) if isinstance(self.appModule.isDelete, dict) else 0
		auto_id = getattr(obj, "UIAAutomationId", "") or ""
		log.debug(f"Chat deletion step: state={state}, role={getattr(obj, 'role', None)}, auto_id={auto_id}")

		if state == 0:
			if obj.role == Role.MENUITEM:
				for item in obj.parent.children:
					if item.firstChild and item.firstChild.name == icons_from_context_menu["delete"]:
						self.appModule.isDelete["state"] = 1
						log.debug("Chat deletion: Clicked delete in context menu")
						item.doAction()
						return True
				log.warning("Chat deletion: Delete option not found in context menu")
				self.appModule.isDelete = False
				CACHED_KEYS["escape"].send()
				return True
			else:
				self.appModule.isDelete = False
				return False

		elif state == 1 and (obj.role in (Role.CHECKBOX, Role.BUTTON, Role.DIALOG, Role.PANE) or auto_id in ("PrimaryButton", "SecondaryButton", "RevokeCheck", "CheckBox")):
			checkbox, primary_button, secondary_button = self._resolve_dialog_elements(obj)
			log.debug(f"Chat deletion dialog resolved: checkbox={checkbox is not None}, primary_button={primary_button is not None}, secondary_button={secondary_button is not None}")

			is_complete = self.appModule.isDelete.get("isCompleteDeletion", False)
			if checkbox:
				is_checked = State.CHECKED in getattr(checkbox, "states", set())
				log.debug(f"Chat deletion checkbox: is_checked={is_checked}, target_is_complete={is_complete}")
				if is_complete and not is_checked:
					checkbox.doAction()
					log.debug("Chat deletion: Toggled checkbox to checked")
				elif not is_complete and is_checked:
					checkbox.doAction()
					log.debug("Chat deletion: Toggled checkbox to unchecked")

			# Determine specific announcement message if not audio mode
			if not conf.get("audioPlaybackWhenDeleted"):
				btn_name = (getattr(primary_button, "name", "") or "").lower()
				chk_name = (getattr(checkbox, "name", "") or "").lower()

				channel_kws = [kw for kws in chat_deletion_keywords.get("channel", {}).values() for kw in kws]
				group_kws = [kw for kws in chat_deletion_keywords.get("group", {}).values() for kw in kws]
				bot_kws = [kw for kws in chat_deletion_keywords.get("bot", {}).values() for kw in kws]

				if any(k in btn_name for k in channel_kws):
					self.appModule.isDelete["message"] = _("You left the channel")
				elif any(k in btn_name for k in group_kws):
					self.appModule.isDelete["message"] = _("You left the group")
				elif any(k in chk_name for k in bot_kws):
					if is_complete:
						self.appModule.isDelete["message"] = _("Bot removed and blocked")
					else:
						self.appModule.isDelete["message"] = _("Bot removed")
				elif is_complete:
					self.appModule.isDelete["message"] = _("Chat deleted on both sides")
				else:
					self.appModule.isDelete["message"] = _("Chat deleted")

			if not primary_button:
				log.warning("PrimaryButton not found in chat deletion dialog")
				self.appModule.isDelete = False
				return False

			# If confirmation setting is enabled, do not click. Focus on Delete and let user confirm.
			if conf.get("confirmation_at_deletion"):
				log.debug("Chat deletion: confirmation_at_deletion is True, focusing PrimaryButton")
				self.appModule.isDelete["state"] = "awaiting_confirmation"
				try:
					primary_button.setFocus()
				except Exception as e:
					log.debug(f"Chat deletion: Failed to set focus on PrimaryButton: {e}")
				return False

			# Automatic confirmation mode:
			log.debug("Chat deletion: confirmation_at_deletion is False, invoking PrimaryButton")
			primary_button.doAction()

			# Restore focus prioritizing initial, then next, then previous chat
			self.restore_deletion_focus()
			self.appModule.isDelete["state"] = 2
			return True

		elif state == "awaiting_confirmation":
			dismiss_source = self.appModule.isDelete.get("confirmed_dismissal")
			if not dismiss_source:
				return False

			log.debug(f"Chat deletion: dialog closed via {dismiss_source}, restoring focus")
			delete_msg = self.appModule.isDelete.get("message")
			focused_candidate = self.restore_deletion_focus()
			self.appModule.isDelete = False

			if focused_candidate in ("next", "previous", "fallback"):
				log.debug("Chat was deleted, announcing result")
				if delete_msg == "audio":
					playWaveFile(os.path.join(BASE_DIR, "delete.wav"))
				elif delete_msg:
					message(delete_msg)
			elif focused_candidate == "initial":
				log.debug("Chat deletion was cancelled, focus returned to initial object")

			return False

		elif state == 2:
			if not self.is_chat_item(obj):
				log.debug("Chat deletion state 2: ignoring intermediate element")
				return True
			log.debug(f"Chat deletion state {state} completed, announcing result")
			if self.appModule.isDelete.get("message") == "audio":
				playWaveFile(os.path.join(BASE_DIR, "delete.wav"))
			else:
				message(self.appModule.isDelete.get("message", ""))
			message(formatChatElementOnFocus(obj))
			self.appModule.isDelete = False
			return True

		return False
