# -*- coding:utf-8 -*-
# UnigramAccess: Chat list interaction logic (delete chat, leave group/channel, remove bot, etc.).

import os

import api
from controlTypes import Role, State
import core
from nvwave import playWaveFile
import queueHandler
import scriptHandler
import speech
from ui import message

import addonHandler

addonHandler.initTranslation()

from .cnf import conf
from .data import chat_deletion_keywords
from .unigram_formatting import formatChatElementOnFocus
from .unigram_logger import ulog as log
from .unigram_utils import BASE_DIR, CACHED_KEYS, find_and_activate_context_menu_item


class Title_change_tracking:
	"""Polling loop that monitors chat title/status changes.

	Detects typing indicators, online/offline transitions, and member count
	updates in the foreground chat, announcing them to the user.
	Uses core.callLater with a 500 ms interval.
	"""

	active = False
	pause = False
	interval = 0.5
	savedItems = False

	@classmethod
	def tick(cls):
		if not cls.active or cls.pause:
			return
		title = cls.savedItems.get("profile name")
		if not title or not title.isInForeground:
			cls.pause = True
			return False
		lastProfileName = cls.savedItems.get("last profile name") or ("",)
		if title.childCount > 1 and title.lastChild.name != lastProfileName[-1]:
			if title.firstChild.name == lastProfileName[0]:
				# Announce changes only if not related to switching to another chat
				text = title.lastChild.name
				queueHandler.queueFunction(queueHandler.eventQueue, message, text)
			newTitle = [item.name for item in title.children]
			cls.savedItems.save("last profile name", newTitle)
		core.callLater(int(cls.interval * 1000), cls.tick)

	@classmethod
	def toggle(cls, savedItems=False):
		if not conf.get("automatically announce activity in chats") or not savedItems:
			cls.savedItems = savedItems
			cls.active = True
			cls.pause = False
			conf.set("automatically announce activity in chats", True)
			core.callLater(int(cls.interval * 1000), cls.tick)
			return True
		else:
			cls.active = False
			conf.set("automatically announce activity in chats", False)
			return False

	@classmethod
	def restore(cls, savedItems=False):
		cls.pause = False
		cls.active = True
		cls.savedItems = savedItems
		cls.savedItems.save("last profile name", None)
		core.callLater(int(cls.interval * 1000), cls.tick)


class UnigramChats:
	"""Handles chat-level interactions and deletion in Unigram."""

	def __init__(self, appModule):
		self.appModule = appModule

	def activate_option_for_menu(self, option):
		"""Open context menu on chat item and automatically select a specific option."""
		if self.appModule.executeContextMenuOption:
			return False
		self.appModule.executeContextMenuOption = option
		CACHED_KEYS["Applications"].send()
		return True

	def select_chat(self):
		"""Switch focused chat to selection mode via context menu."""
		return self.activate_option_for_menu("select")

	def pin_chat(self):
		"""Pin or unpin focused chat via context menu."""
		return self.activate_option_for_menu("pin")

	def read_chat(self):
		"""Mark focused chat as read/unread via context menu."""
		return self.activate_option_for_menu("read")

	def to_contacts_list(self):
		"""Focus the contacts list if the Contacts dialog is currently open.

		Returns:
			bool: True if inside Contacts dialog and handled, False otherwise.
		"""
		contacts = self.appModule.ui_helper.get_contacts_list()
		if contacts:
			try:
				focusObj = api.getFocusObject()
				if focusObj == contacts or (
					getattr(focusObj, "role", None) == Role.LISTITEM
					and getattr(focusObj, "parent", None) == getattr(contacts, "parent", None)
				):
					message(getattr(focusObj, "name", ""))
				else:
					contacts.setFocus()
			except Exception as e:
				log.debugException(f"to_contacts_list: contacts.setFocus error: {e}")
			return True
		return False

	def to_chats_list(self):
		"""Focus the chats list (last focused chat item or first item).

		Returns:
			bool: True if handled, False if chat list was not found or inside modal dialog.
		"""
		# If currently inside a modal dialog (such as Contacts dialog), yield to dialog handlers
		curr = api.getFocusObject()
		while curr:
			if getattr(curr, "role", None) == Role.DIALOG:
				return False
			curr = getattr(curr, "parent", None)

		obj = api.getFocusObject()
		lastFocusChatElement = self.appModule.saved_items.get("last focused chat")
		if lastFocusChatElement and getattr(lastFocusChatElement, "location", None) and lastFocusChatElement.location.width:
			if obj == lastFocusChatElement:
				message(getattr(obj, "name", ""))
			else:
				lastFocusChatElement.setFocus()
			return True

		try:
			targetList = self.appModule.ui_helper.getChatsListElement()
		except Exception:
			targetList = None

		if not targetList:
			return False

		first = getattr(targetList, "firstChild", None)
		if first:
			target = first
			if getattr(target, "role", None) == Role.BUTTON and getattr(target, "next", None):
				target = target.next
			if getattr(target, "role", None) == Role.LISTITEM:
				target.setFocus()
				return True

		message(_("Chat list is empty"))
		return True

	def to_threads_list(self):
		"""Focus the forum topics/threads list in a supergroup.

		Returns:
			bool: True if threads list was found and focused, False otherwise.
		"""
		branch_list = self.appModule.ui_helper.get_branch_list()
		if branch_list and getattr(branch_list, "firstChild", None):
			branch_list.firstChild.setFocus()
			return True
		return False

	def to_profile_panel(self):
		"""Focus the profile information panel.

		Returns:
			bool: True if profile panel was found and focused, False otherwise.
		"""
		profile_panel = self.appModule.ui_helper.get_profile_panel()
		if profile_panel:
			profile_panel.setFocus()
			return True
		return False

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
			str: 'initial', 'next', or 'previous' depending on which candidate was focused,
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

		log.warning("Chat focus restoration failed: None of the three candidates (initial, next, previous) could be identified or focused")
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
		"""
		if not conf.get("confirmation_at_deletion"):
			speech.cancelSpeech()

		state = self.appModule.isDelete.get("state", 0) if isinstance(self.appModule.isDelete, dict) else 0
		auto_id = getattr(obj, "UIAAutomationId", "") or ""
		log.debug(f"Chat deletion step: state={state}, role={getattr(obj, 'role', None)}, auto_id={auto_id}")

		if state == 0:
			if find_and_activate_context_menu_item(obj, "delete", close_on_failure=True):
				self.appModule.isDelete["state"] = 1
				log.debug("Chat deletion: Clicked delete in context menu")
				return True
			else:
				log.warning("Chat deletion: Delete option not found in context menu")
				self.appModule.isDelete = False
				return True

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

				lang = conf.get("lang")
				channel_kws = chat_deletion_keywords.get("channel", {}).get(lang, ())
				group_kws = chat_deletion_keywords.get("group", {}).get(lang, ())
				bot_kws = chat_deletion_keywords.get("bot", {}).get(lang, ())

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
			self.appModule.isDelete["confirmed_dismissal"] = "primary"
			self.appModule.isDelete["state"] = "awaiting_confirmation"
			primary_button.doAction()
			return True

		elif state == "awaiting_confirmation":
			dismiss_source = self.appModule.isDelete.get("confirmed_dismissal")
			if not dismiss_source:
				return False

			log.debug(f"Chat deletion: dialog closed via {dismiss_source}, restoring focus")
			delete_msg = self.appModule.isDelete.get("message")
			focused_candidate = self.restore_deletion_focus()
			self.appModule.isDelete = False

			if dismiss_source == "primary" and focused_candidate != "initial":
				log.debug(f"Chat was deleted (dismissal={dismiss_source}), announcing result")
				if delete_msg == "audio":
					playWaveFile(os.path.join(BASE_DIR, "delete.wav"))
				elif delete_msg:
					message(delete_msg)
			else:
				log.debug(f"Chat deletion was cancelled via {dismiss_source}")

			if not focused_candidate:
				log.warning(f"Chat deletion: none of the three candidates (initial, next, previous) could be identified or focused (dismissal={dismiss_source})")

			return False

		return False

	def script_read_profile_name(self, gesture):
		"""Announce chat title; pressed twice: enable or disable tracking of changes in the chat title."""
		if scriptHandler.getLastScriptRepeatCount() == 1:
			if Title_change_tracking.toggle(self.appModule.saved_items): message(_("Chat activity tracking is enabled"))
			else: message(_("Chat activity tracking is disabled"))
			return
		isGroupCall = False
		title = False
		obj = self.appModule.saved_items.get("profile name")
		if obj and obj.location.width != 0:
			title = obj
			message(obj.name)
		for item in self.appModule.ui_helper.getElements():
			if not title and item.role == Role.BUTTON and item.UIAAutomationId == "Profile":
				message(item.name)
				title = item
		if not title:
			profile_panel = self.appModule.ui_helper.get_profile_panel()
			if profile_panel:
				header = next((item for item in profile_panel.children if item.UIAAutomationId == "HeaderDetailsPresenter"), None)
				if header:
					title = header
					message(header.name)
		if not title:
			message(_("Failed to read chat title"))
		if title:
			self.appModule.saved_items.save("profile name", title)

	def script_showMoreOptions(self, gesture):
		"""Open the More Options menu in an open chat via the SearchOption sibling."""
		search_btn = next(
			(
				item
				for item in self.appModule.ui_helper.getElements()
				if getattr(item, "role", None) == Role.BUTTON
				and getattr(item, "UIAAutomationId", "") == "SearchOption"
			),
			None,
		)

		targetButton = search_btn.next if (search_btn and getattr(search_btn, "next", None) and getattr(search_btn.next, "role", None) == Role.BUTTON) else None
		if targetButton:
			targetButton.doAction()
		else:
			message(_("Button not found"))

