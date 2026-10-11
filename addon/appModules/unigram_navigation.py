# -*- coding:utf-8 -*-
import re
import addonHandler
addonHandler.initTranslation()
from controlTypes import Role, State
from keyboardHandler import KeyboardInputGesture
import api
import core
from ui import message
from .cnf import conf
from .data import unread_messages_keywords
from .unigram_formatting import announceFolderChange
from .unigram_logger import ulog as log

class UnigramNavigation:
	def __init__(self, appModule):
		self.appModule = appModule

	def script_toChatList(self, gesture, arg = False):
		log.info("Executing toChatList shortcut.")
		# Priority 1: If a forum group's topics list is open, focus topics list
		if getattr(self.appModule, "chats_helper", None) and self.appModule.chats_helper.to_threads_list():
			return True

		# Priority 2: Focus the main chats list
		if getattr(self.appModule, "chats_helper", None) and self.appModule.chats_helper.to_chats_list():
			return True

		# Priority 3: If Contacts dialog is active, focus the contacts list
		if getattr(self.appModule, "chats_helper", None) and self.appModule.chats_helper.to_contacts_list():
			return True

		# Priority 4: If in Settings, focus settings categories list
		if getattr(self.appModule, "settings_helper", None) and self.appModule.settings_helper.to_categories_list():
			return True

		if not arg:
			message(_("List not found"))
	def script_toDetailPanel(self, gesture):
		log.info("Executing toDetailPanel shortcut.")
		# Priority 1: Focus or move caret to last message in active chat
		if getattr(self.appModule, "msg_helper", None) and self.appModule.msg_helper.to_last_message():
			return True

		# Priority 2: Focus profile panel if open
		if getattr(self.appModule, "chats_helper", None) and self.appModule.chats_helper.to_profile_panel():
			return True

		# Priority 3: Focus settings detail panel if in settings
		if getattr(self.appModule, "settings_helper", None) and self.appModule.settings_helper.to_detail_panel():
			return True

		message(_("Section not found"))

	script_toLastMessage = script_toDetailPanel

	def get_tabs_folder_element(self):
		"""Retrieve and cache the chat folders container element (top bar or side bar)."""
		obj = self.appModule.saved_items.get("tabs folder")
		if not (obj and getattr(obj, "location", None) and obj.location.width):
			for item in self.appModule.ui_helper.getElements():
				if getattr(item, "UIAAutomationId", "") in ("ChatFolders", "ChatFoldersSide"):
					obj = item
					self.appModule.saved_items.save("tabs folder", obj)
					break
			if not obj:
				list_elem = self.appModule.ui_helper.getChatsListElement()
				if list_elem and getattr(list_elem, "previous", None):
					prev = list_elem.previous
					if getattr(prev, "UIAAutomationId", "") in ("ChatFolders", "ChatFoldersSide"):
						obj = prev
						self.appModule.saved_items.save("tabs folder", obj)
		return obj if (obj and getattr(obj, "location", None) and obj.location.width) else None

	def script_to_tabs_folder(self, gesture):
		obj = self.get_tabs_folder_element()
		if obj:
			children = [item for item in getattr(obj, "children", []) if getattr(item, "location", None) and item.location.width]
			if children:
				el = next((item for item in children if State.SELECTED in getattr(item, "states", set())), children[0])
				el.setFocus()
				return
		message(_("Chat folder list not found"))

	def script_switch_chat_folder(self, gesture):
		gesture.send()
		if not conf.get("voiceFolderNames"):
			return

		key = getattr(gesture, "mainKeyName", "") or getattr(gesture, "displayName", "") or getattr(gesture, "id", "")
		match = re.search(r"(\d)$", key)
		idx = int(match.group(1)) - 1 if match else None

		if idx == 8:
			message(_("Archived chats"))
			return

		obj = self.get_tabs_folder_element()
		if not obj:
			return
		children = [item for item in getattr(obj, "children", []) if getattr(item, "location", None) and item.location.width]
		if not children:
			return

		if idx is not None and 0 <= idx < len(children):
			announceFolderChange(children[idx])

	def script_switch_chat(self, gesture):
		gesture.send()
		if not conf.get("voiceChatNames", True):
			return

		self.appModule.isSwitchingChat = True
		profile = self.appModule.saved_items.get("profile name")
		if not profile or not getattr(profile, "isFocusable", False):
			profile = next((item for item in self.appModule.ui_helper.getElements() if item.role in (Role.BUTTON, Role.LINK) and item.UIAAutomationId == "Profile"), None)
			if profile and getattr(profile, "isFocusable", False):
				self.appModule.saved_items.save("profile name", profile)

		if not profile:
			return

		children = getattr(profile, "children", []) or []
		if children and getattr(children[0], "name", None):
			name = children[0].name.strip()
			if name:
				message(name)

	def _is_unread_messages_separator(self, obj):
		"""Check if a message list item represents the unread messages separator."""
		if not obj:
			return False

		try:
			unread_kws = unread_messages_keywords.get(conf.get("lang"), ())
			name = (getattr(obj, "name", None) or "").strip().lower()
			if any(kw in name for kw in unread_kws):
				return True

			first_child = getattr(obj, "firstChild", None)
			if first_child and getattr(first_child, "role", None) == Role.BUTTON:
				child_name = (getattr(first_child, "name", None) or "").strip().lower()
				if any(kw in child_name for kw in unread_kws):
					return True

				# FALLBACK (TEMPORARY):
				# For unverified languages not yet added to the dictionary, safely detect
				# the separator button via the down-arrow icon glyph (\ue0e5).
				# This fallback may be removed once dictionary keywords for all supported
				# languages are verified through manual inspection.
				for item in getattr(first_child, "children", []):
					if getattr(item, "name", None) == "\ue0e5":
						return True
		except Exception as e:
			log.debugException(f"Swallowed exception: {e}")

		return False

	def script_goToTheLastUnreadMessage(self, gesture):
		messages = self.appModule.ui_helper.getMessagesElement()
		if not messages:
			message(_("No open chat"))
			return False

		try:
			last_obj = messages.lastChild
		except Exception:
			last_obj = None

		if not last_obj:
			message(_("This chat is empty"))
			return False

		target_item = None
		while last_obj:
			if self._is_unread_messages_separator(last_obj):
				target_item = last_obj
				break
			try:
				last_obj = last_obj.previous
			except Exception:
				break

		if target_item:
			try:
				# Focus the inner button directly if focusable, otherwise the list item
				first_child = getattr(target_item, "firstChild", None)
				if first_child and getattr(first_child, "role", None) == Role.BUTTON and getattr(first_child, "isFocusable", False):
					first_child.setFocus()
				else:
					target_item.setFocus()
			except Exception:
				try:
					target_item.setFocus()
				except Exception as e:
					log.debugException(f"Swallowed exception: {e}")
		else:
			message(_("Unread message not found"))

	def script_showMenu(self, gesture):
		try:
			targetButton = next((item for item in self.appModule.ui_helper.getElements() if item.UIAAutomationId == "Photo" and item.role == Role.TOGGLEBUTTON), False)
		except Exception: targetButton = False
		if targetButton: targetButton.doAction()
		else: message(_("Navigation menu not available"))

	def script_openProfile(self, gesture):
		profile = self.appModule.saved_items.get("profile name")
		if not profile or not getattr(profile, "isFocusable", False):
			profile = next((item for item in self.appModule.ui_helper.getElements() if item.role in (Role.BUTTON, Role.LINK) and item.UIAAutomationId == "Profile"), None)
			if profile and getattr(profile, "isFocusable", False):
				self.appModule.saved_items.save("profile name", profile)

		if profile and getattr(profile, "isFocusable", False):
			self.appModule.isOpenProfile = api.getFocusObject()
			profile.doAction()
			core.callLater(200, self._focus_profile_on_open)
		else:
			message(_("Chat profile not found"))

	def _focus_profile_on_open(self):
		ui_helper = getattr(self.appModule, "ui_helper", None)
		if not ui_helper:
			return
		panel = next((item for item in ui_helper.getElements() if ui_helper._is_profile_host(item)), None)
		if panel and getattr(panel, "firstChild", None):
			try:
				panel.firstChild.setFocus()
			except Exception as e:
				log.debugException(f"_focus_profile_on_open error: {e}")

	def script_to_down(self, gesture):
		button = next((button for button in self.appModule.ui_helper.getElements() if button.role == Role.BUTTON and button.UIAAutomationId == "MessagesButton"), None)
		if button:
			button.doAction()
		else:
			message(_("Scroll down button not found"))

	def script_go_to_list_search_results(self, gesture):
		btn = next((element.next for element in self.appModule.ui_helper.getElements()
			if element.role == Role.EDITABLETEXT and element.UIAAutomationId == "Field" and "/" in element.next.name and element.next.role == Role.BUTTON), None)
		if btn:
			btn.doAction()
		else:
			message(_("Search is not active"))
	
	def script_go_to_next_search_result(self, gesture):
		"""Navigate to the next search result (upwards in chat history, clicking SearchPrevious)."""
		btn = next((element for element in self.appModule.ui_helper.getElements()
			if element.UIAAutomationId == "SearchPrevious" and element.role == Role.BUTTON), None)
		if btn and State.FOCUSABLE in btn.states:
			btn.doAction()
		elif btn:
			message(_("No next search result"))
		else:
			message(_("Search is not active"))

	def script_go_to_previous_search_result(self, gesture):
		"""Navigate to the previous search result (downwards towards newer messages, clicking SearchNext)."""
		btn = next((element for element in self.appModule.ui_helper.getElements()
			if element.UIAAutomationId == "SearchNext" and element.role == Role.BUTTON), None)
		if btn and State.FOCUSABLE in btn.states:
			btn.doAction()
		elif btn:
			message(_("No previous search result"))
		else:
			message(_("Search is not active"))
