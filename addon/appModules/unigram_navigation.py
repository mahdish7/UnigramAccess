# -*- coding:utf-8 -*-
import addonHandler
addonHandler.initTranslation()
from controlTypes import Role, State
from keyboardHandler import KeyboardInputGesture
import api
from ui import message
import scriptHandler
from .data import unread_messages_keywords
from .trackers import Title_change_tracking
from .unigram_logger import ulog as log

class UnigramNavigation:
	def __init__(self, appModule):
		self.appModule = appModule

	def script_toChatList(self, gesture, arg = False):
		log.info("Executing toChatList shortcut.")
		obj = api.getFocusObject()
		lastFocusChatElement = self.appModule.saved_items.get("last focused chat")
		if lastFocusChatElement and lastFocusChatElement.location and lastFocusChatElement.location.width:
			if obj == lastFocusChatElement: message(obj.name)
			else: lastFocusChatElement.setFocus()
			return
		try: targetList = self.appModule.ui_helper.getChatsListElement()
		except Exception: targetList = None
		if not targetList:
			settings_list = self.appModule.ui_helper.get_settings_list()
			if settings_list:
				settings_list.setFocus()
				return True
			if not arg: message(_("Chat list not found"))
			return
		if targetList.firstChild:
			targetList = targetList.firstChild
			if targetList.role == Role.BUTTON and targetList.next: targetList =  targetList.next
			if targetList.role and targetList.role == Role.LISTITEM:
				targetList.setFocus()
				return
		if not arg: message(_("Chat list is empty"))

	def script_toLastMessage(self, gesture):
		focusObj = api.getFocusObject()
		if self.appModule.ui_helper.is_message_object(focusObj):
			if focusObj.parent.next: KeyboardInputGesture.fromName("end").send()
			else: message(focusObj.name)
			return True
		obj = self.appModule.ui_helper.getMessagesElement()
		try:
			obj.lastChild.setFocus()
			KeyboardInputGesture.fromName("end").send()
		except Exception:
			if obj and not obj.lastChild:
				message(_("This chat is empty"))
				return True
			branch_list = self.appModule.ui_helper.get_branch_list()
			if branch_list:
				branch_list.firstChild.setFocus()
				return
			profile_panel = self.appModule.ui_helper.get_profile_panel()
			if profile_panel:
				profile_panel.setFocus()
				return
			settings_panel = self.appModule.ui_helper.get_settings_panel()
			if settings_panel:
				settings_panel.setFocus()
				return
			message(_("No open chat"))

	def script_to_tabs_folder(self, gesture):
		obj = self.appModule.saved_items.get("tabs folder")
		if obj and obj.location and obj.location.width:
			el = next((item for item in self.appModule.tabsFolderElement.children if State.SELECTED in item.states), None)
			if el: el.setFocus()
			else: message(_("Chat folder list not found"))
		else:
			list = self.appModule.ui_helper.getChatsListElement()
			if list:
				obj = list.previous
				self.appModule.saved_items.save("tabs folder", obj)
				el = next((item for item in obj.children if State.SELECTED in item.states), None)
				if el: el.setFocus()
				else: message(_("Chat folder list not found"))
			else: message(_("Chat folder list not found"))

	def script_move_focus_to_list_threads(self, gesture):
		branch_list = self.appModule.ui_helper.get_branch_list()
		if branch_list: branch_list.firstChild.setFocus()
		else: message(_("No list with threads was found"))

	def script_to_open_profile(self, gesture):
		profile_panel = self.appModule.ui_helper.get_profile_panel()
		if profile_panel: profile_panel.setFocus()
		else: message(_("There is no open profile"))

	def script_read_profile_name(self, gesture):
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
			elif item.role == Role.LINK and item.UIAAutomationId == "GroupCall": isGroupCall = item.firstChild.name
		if title:
			self.appModule.saved_items.save("profile name", title)
			if isGroupCall: message(isGroupCall)
		else: message(_("No open chat"))

	def _is_unread_messages_separator(self, obj):
		"""Check if a message list item represents the unread messages separator."""
		if not obj:
			return False

		try:
			# Primary detection: Match item name against verified dictionary keywords
			unread_kws = [kw for kws in unread_messages_keywords.values() for kw in kws]
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
		except Exception:
			pass

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
				except Exception:
					pass
		else:
			message(_("There are no unread messages in this chat"))

	def script_showMenu(self, gesture):
		try:
			targetButton = next((item for item in self.appModule.ui_helper.getElements() if item.UIAAutomationId == "Photo" and item.role == Role.TOGGLEBUTTON), False)
		except Exception: targetButton = False
		if targetButton: targetButton.doAction()
		else: message(_("Navigation menu not available"))

	def script_openProfile(self, gesture):
		profile = self.appModule.saved_items.get("profile name")
		if not profile or profile.location.width == 0:
			profile = next((item for item in self.appModule.ui_helper.getElements() if item.role ==Role.BUTTON and item.UIAAutomationId == "Profile"), None)
			if profile:
				self.appModule.saved_items.save("profile name", profile)
		if profile and profile.location.width != 0:
			self.appModule.isOpenProfile = api.getFocusObject()
			profile.doAction()
		else:
			message(_("No open chat"))

	def script_to_down(self, gesture):
		button = next((button for button in self.appModule.ui_helper.getElements() if button.role == Role.BUTTON and button.UIAAutomationId == "MessagesButton"), None)
		if button: button.doAction()
		else: message(_("Button not found"))

	def script_go_to_list_search_results(self, gesture):
		obj = api.getFocusObject()
		btn = next((element.next for element in self.appModule.ui_helper.getElements()
			if element.role == Role.EDITABLETEXT and element.UIAAutomationId == "Field" and "/" in element.next.name and element.next.role == Role.BUTTON), None)
		if btn:
			btn.doAction()
		else: message(_("Button not found"))
	
	def script_go_to_previous_search_result(self, gesture):
		obj = api.getFocusObject()
		btn = next((element for element in self.appModule.ui_helper.getElements()
			if element.UIAAutomationId == "SearchPrevious"and element.role == Role.BUTTON), None)
		if btn and State.FOCUSABLE in btn.states: btn.doAction()
		elif btn: message(_("No next search result"))
		else: message(_("Button not found"))
	
	def script_go_to_next_search_result(self, gesture):
		obj = api.getFocusObject()
		btn = next((element for element in self.appModule.ui_helper.getElements()
			if element.UIAAutomationId == "SearchNext"and element.role == Role.BUTTON), None)
		if btn and State.FOCUSABLE in btn.states: btn.doAction()
		elif btn: message(_("No previous search result"))
		else: message(_("Button not found"))
