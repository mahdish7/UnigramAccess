# -*- coding:utf-8 -*-
# UnigramAccess
# Copyright (C) 2026 Mahdi Sharifi <mahdii.sh7@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

"""App module for Unigram (Telegram client for Windows) providing
enhanced accessibility through keyboard shortcuts, message formatting,
voice message controls, call management, and live chat monitoring.
"""

# Standard library imports
import os
import re

# NVDA core imports
import api
import appModuleHandler
from controlTypes import Role, State
from scriptHandler import script
import speech
from ui import message

import addonHandler

addonHandler.initTranslation()

# Local module imports
from .cnf import conf
from .data import (
	composer_header_title_replacements,
	keywordsInMessages,
)
from .overlays import (
	Audio_and_video_button,
	EditableText,
	Media_download_button,
	Message_list_item,
	SettingsPanelListItem,
	SettingsRadioListItem,
)
from .text_window import TextWindow
from .unigram_calls import UnigramCalls
from .unigram_formatting import (
	formatChatElementOnFocus,
	formatMediaButtonName,
	formatMediaButtonOnFocus,
	formatMessageOnFocus,
	formatPollOption,
	resolveUnlabeledElement,
)
from .unigram_logger import ulog as log
from .unigram_chats import Title_change_tracking, UnigramChats
from .unigram_media import UnigramMedia
from .unigram_messages import Chat_update, UnigramMessages
from .unigram_navigation import UnigramNavigation
from .unigram_settings import UnigramSettings
from .unigram_ui import Saved_items, UnigramUIHelper
from .unigram_utils import CACHED_KEYS, find_and_activate_context_menu_item


class AppModule(appModuleHandler.AppModule):
	"""Main application module for Unigram.

	Acts as the central orchestrator, delegating domain-specific logic to
	dedicated helper modules while maintaining scripts (keyboard shortcuts),
	event handlers, and overlay class injection that must reside in the
	AppModule per NVDA architecture requirements.
	"""

	# ── Class Attributes ────────────────────────────────────────────────

	scriptCategory = "UnigramAccess"

	# State tracking flags
	profilePanelElement = False
	isDelete = False
	isOpenProfile = False
	executeContextMenuOption = False
	isMedia = False
	isMessageSelectionMode = False
	_selection_restore_target = None

	# ── Initialization & Teardown ───────────────────────────────────────

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.saved_items = Saved_items()

		# Restore background polling timers if they were active
		if conf.get("automatically announce new messages") and not Chat_update.active:
			Chat_update.restore(self)
		if conf.get("automatically announce activity in chats") and not Title_change_tracking.active:
			Title_change_tracking.restore(self.saved_items)

		# Initialize helper modules
		self.ui_helper = UnigramUIHelper(self)
		self.settings_helper = UnigramSettings(self)
		self.nav_helper = UnigramNavigation(self)
		self.call_helper = UnigramCalls(self)
		self.msg_helper = UnigramMessages(self)
		self.chats_helper = UnigramChats(self)
		self.media_helper = UnigramMedia(self)

	# ── Overlay Class Injection ─────────────────────────────────────────

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		"""Dynamically inject custom overlay classes into Unigram UI elements.

		Inspects each NVDAObject and prepends appropriate overlay classes
		for messages, settings panel items, editable text fields, call buttons,
		sliders, and progress bars.
		"""
		import comtypes

		try:
			if obj.role == Role.LISTITEM and obj.isFocusable:
				parent = getattr(obj, "parent", None)
				parentId = getattr(parent, "UIAAutomationId", "") if parent else ""

				if parentId in ("ChatFolders", "ChatsList", "TopicList") or (getattr(self, "chats_helper", None) and self.chats_helper.is_topic_item(obj)):
					return

				elif parentId == "Navigation":
					clsList.insert(0, SettingsPanelListItem)
					return True

				name = getattr(obj, "name", "") or ""
				sender = ""
				keywords = keywordsInMessages.get(conf.get("lang"), keywordsInMessages["en"])
				if keywords[3] in name:
					sender = "received"
				elif keywords[2] in name:
					sender = "send"
				obj.sender_message = sender
				obj.end_text = name
				if (
					obj.sender_message
					or (parent and parentId == "Messages")
					or getattr(obj, "UIAAutomationId", "") == "Message_item"
				):
					clsList.insert(0, Message_list_item)
					return

				# Check whether this list item wraps an inner RadioButton (e.g. Proxy, Language, and settings lists)
				firstChild = getattr(obj, "firstChild", None)
				if firstChild and getattr(firstChild, "role", None) == Role.RADIOBUTTON:
					clsList.insert(0, SettingsRadioListItem)
					return

			elif (
				conf.get("action_when_pressing_up_arrow_in_text_field") != "edit"
				and obj.role == Role.EDITABLETEXT
				and obj.UIAAutomationId == "TextField"
			):
				clsList.insert(0, EditableText)

			elif obj.role == Role.BUTTON and obj.UIAAutomationId == "Profile":
				self.saved_items.save("profile name", obj)

			elif obj.UIAAutomationId in ("Audio", "Video"):
				clsList.insert(0, Audio_and_video_button)

			elif obj.role in (Role.SLIDER, Role.UNKNOWN) and getattr(obj, "UIAAutomationId", "") == "Slider":
				self.saved_items.save("slider", obj)

			elif getattr(obj, "UIAAutomationId", "") in ("Button", "Download") and getattr(obj, "role", None) in (Role.BUTTON, Role.LINK):
				clsList.insert(0, Media_download_button)

		except (comtypes.COMError, AttributeError) as e:
			log.debugException(f"Handled expected exception during chooseNVDAObjectOverlayClasses: {e}")
		except Exception as e:
			log.error(f"Unexpected exception in chooseNVDAObjectOverlayClasses: {e}", exc_info=True)

	def getScript(self, gesture):
		if self.isDelete and isinstance(self.isDelete, dict) and self.isDelete.get("state") == "awaiting_confirmation":
			# Record confirmation / cancellation on Enter or Space
			gesture_ids = getattr(gesture, "identifiers", []) or []
			vk_code = getattr(gesture, "vkCode", None)
			is_enter = (vk_code == 13) or any(i in ("kb:enter", "kb:numpadEnter", "kb:numpadenter") for i in gesture_ids)
			is_space = (vk_code == 32) or any(i == "kb:space" for i in gesture_ids)

			if is_enter or is_space:
				try:
					focus_obj = api.getFocusObject()
					auto_id = getattr(focus_obj, "UIAAutomationId", "") or ""
					if is_enter:
						self.isDelete["confirmed_dismissal"] = "secondary" if auto_id == "SecondaryButton" else "primary"
						log.debug(f"Delete dialog: confirmed dismissal via {self.isDelete['confirmed_dismissal']} (Enter on {auto_id})")
					elif is_space and auto_id in ("PrimaryButton", "SecondaryButton"):
						self.isDelete["confirmed_dismissal"] = "secondary" if auto_id == "SecondaryButton" else "primary"
						log.debug(f"Delete dialog: confirmed dismissal via {auto_id} (Space)")
				except Exception as e:
					log.debug(f"Error checking focus in getScript: {e}")

		return super().getScript(gesture)

	# ── Focus Event Handler ─────────────────────────────────────────────

	def event_gainFocus(self, obj, nextHandler):
		"""Handle focus changes across the Unigram application.

		Orchestrates timer restoration, slider focus management, state machine
		flag processing, and element-specific formatting/labeling.
		"""
		objId = getattr(obj, "UIAAutomationId", "")
		objName = getattr(obj, "name", "")
		if objId or objName:
			role = getattr(obj, "role", None)
			roleName = getattr(role, "name", str(role)) if role else "Unknown"
			log.debug(f"Focus changed: Role: {roleName} ({role}) - ID: '{objId}'")

		if self.ui_helper.is_message_object(obj) and State.SELECTED in getattr(obj, "states", set()):
			self.isMessageSelectionMode = True
			log.debug("Message selection mode activated")

		# Restore background timers if window was minimized
		if self._restoreBackgroundTimers():
			pass  # Timers restored, continue processing

		# Handle slider focus restoration
		if self._handleSliderFocusRestoration(obj):
			return

		# Handle state machine flags
		if self._handleStateMachineFlags(obj):
			return

		# Format and enrich focused object
		self._formatFocusedObject(obj)

		if getattr(obj, "UIAAutomationId", "") in ("Button", "Download"):
			self.media_helper.start_download_monitoring(obj)

		nextHandler()

	def event_nameChange(self, obj, nextHandler):
		if getattr(obj, "UIAAutomationId", "") in ("Button", "Download"):
			raw_name = ""
			uia_elem = getattr(obj, "UIAElement", None)
			if uia_elem:
				try:
					raw_name = getattr(uia_elem, "CurrentName", "") or getattr(uia_elem, "currentName", "") or ""
				except Exception as e:
					log.debugException(f"Swallowed exception: {e}")
			if not raw_name:
				try:
					raw_name = obj._get_name()
				except Exception as e:
					log.debugException(f"Swallowed exception: {e}")
			if raw_name:
				obj.name = formatMediaButtonName(obj, raw_name)
			if obj == api.getFocusObject():
				self.media_helper.start_download_monitoring(obj)

		nextHandler()

	def _restoreBackgroundTimers(self):
		"""Restore suspended background polling timers after window reactivation."""
		restored = False
		if conf.get("automatically announce new messages"):
			if Chat_update.pause or not Chat_update.active:
				Chat_update.restore(self)
				restored = True
		if conf.get("automatically announce activity in chats"):
			if Title_change_tracking.pause or not Title_change_tracking.active:
				Title_change_tracking.restore(self.saved_items)
				restored = True
		return restored

	def _handleSliderFocusRestoration(self, obj):
		"""Restore focus from a disappeared voice slider to the previous object."""
		savedSliderFocus = getattr(self.media_helper, "saved_slider_focus", None)
		if savedSliderFocus and not self.media_helper._is_slider_element(obj):
			activeSlider = getattr(self.media_helper, "active_slider", None)
			if not self.media_helper._is_slider_alive(activeSlider):
				speech.cancelSpeech()
				self.media_helper.saved_slider_focus = None
				self.media_helper.active_slider = None
				try:
					savedSliderFocus.setFocus()
				except Exception as e:
					log.debugException(f"Swallowed exception: {e}")
				return True
			else:
				self.media_helper.saved_slider_focus = None
				self.media_helper.active_slider = None
		return False

	def _handleStateMachineFlags(self, obj):
		"""Process internal state machine flags that intercept normal focus behavior.

		Returns True if the focus event was consumed (should not call nextHandler).
		"""
		if self._selection_restore_target:
			target = self._selection_restore_target
			self._selection_restore_target = None
			if obj != target and target and getattr(target, "parent", None):
				log.debug("Selection exit: restoring focus to previous message")
				self.msg_helper._safe_set_focus(target)
				return True

		if self.isOpenProfile:
			self.isOpenProfile = False
			if self.ui_helper._is_profile_host(self.profilePanelElement):
				panel = self.profilePanelElement
			else:
				panel = next((item for item in self.ui_helper.getElements() if self.ui_helper._is_profile_host(item)), None)
			if panel:
				self.profilePanelElement = panel
				if panel.firstChild:
					try:
						panel.firstChild.setFocus()
					except Exception as e:
						log.debugException(f"Swallowed exception: {e}")
			return True

		elif self.executeContextMenuOption:
			target = self.executeContextMenuOption
			self.executeContextMenuOption = False
			find_and_activate_context_menu_item(obj, target, close_on_failure=True)
			return True

		elif self.isDelete:
			target = self.isDelete.get("target") if isinstance(self.isDelete, dict) else None
			if target == "chats":
				consumed = self.chats_helper.handle_deletion_step(obj)
			else:
				consumed = self.msg_helper.handle_deletion_step(obj)
			return bool(consumed)

		elif self.isMedia:
			consumed = self.media_helper.handle_media_step(obj)
			return bool(consumed)

		return False
 
	def _restore_selection_focus(self, target):
		"""Fallback timer to restore focus to target message upon selection exit."""
		if self._selection_restore_target == target:
			self._selection_restore_target = None
			if target and getattr(target, "parent", None):
				log.debug("Selection exit: fallback restoring focus to message")
				self.msg_helper._safe_set_focus(target)

	def _formatFocusedObject(self, obj):
		"""Apply formatting and label enrichment to the focused object."""
		if obj.role == Role.LISTITEM:
			speech.cancelSpeech()
			if self.ui_helper.is_message_object(obj):
				self.saved_items.save("last focus object", obj)
				obj.name = formatMessageOnFocus(obj, self.saved_items)
			elif obj.parent.UIAAutomationId == "ChatsList":
				self.saved_items.save("last focused chat", obj)
				obj.name = formatChatElementOnFocus(obj)
			elif getattr(self, "chats_helper", None) and self.chats_helper.is_topic_item(obj):
				self.saved_items.save("last focused topic", obj)
			elif obj.parent.UIAAutomationId == "ScrollingHost":
				if obj.name == "" and obj.childCount != 0:
					for item in obj.children:
						obj.name += item.name
				elif obj.name.startswith("inlineQueryResult"):
					# Processing inline results
					name = [item.name for item in obj.children if item.name != ""]
					obj.name = ". ".join(name)
			elif obj.name == "Unigram.ViewModels.MessageViewModel":
				obj.name = obj.firstChild.name
			elif obj.name.startswith("EETypeRva"):
				obj.name = ", ".join([item.name for item in obj.children[1:]])
			elif obj.name == "Unigram.Entities.StoragePhoto":
				obj.name = _("Image")
			elif obj.name.startswith("chatTheme {"):
				obj.name = obj.firstChild.name
			elif obj.name.startswith("forumTopic {\n  info = forumTopicInfo {"):
				labels = [
					label.name
					for label in obj.children
					if label.UIAAutomationId in ("TitleLabel", "BriefInfo", "TimeLabel")
				]
				obj.name = ". ".join((labels[0], labels[2], labels[1]))

		elif obj.role == Role.EDITABLETEXT:
			try:
				# Determine if this is a message input field and check if its title needs changing
				if getattr(obj, "UIAAutomationId", "") == "TextField":
					# Look for ComposerHeaderReference among immediate previous siblings
					prev = getattr(obj, "previous", None)
					ref = None
					steps = 0
					while prev and steps < 6:
						if getattr(prev, "UIAAutomationId", "") == "ComposerHeaderReference":
							ref = prev
							break
						prev = getattr(prev, "previous", None)
						steps += 1

					if ref:
						title = getattr(ref, "firstChild", None)
						raw_name = getattr(title, "name", "") if (title and getattr(title, "UIAAutomationId", "") == "TitleLabel") else (getattr(ref, "name", "") or "")
						if raw_name:
							obj.name = composer_header_title_replacements.get(raw_name, raw_name)
			except Exception as e:
				log.debugException(f"Swallowed exception: {e}")

		elif obj.role in (Role.BUTTON, Role.LINK):
			try:
				if getattr(obj, "UIAAutomationId", "") in ("Button", "Download"):
					formatMediaButtonOnFocus(obj)
				elif obj.role == Role.LINK and getattr(getattr(obj, "parent", None), "UIAAutomationId", "") in ("TextBlock", "Message"):
					speech.cancelSpeech()
				elif obj.role in (Role.BUTTON, Role.TOGGLEBUTTON):
					# Add labels for call buttons
					if obj.UIAAutomationId == "Audio" and getattr(obj.firstChild, "name", "") == "\ue720" and getattr(obj.next, "UIAAutomationId", "") == "AudioInfo":
						obj.name = obj.next.name
					elif obj.UIAAutomationId == "Video":
						first_child_name = getattr(getattr(obj, "firstChild", None), "name", "")
						if first_child_name == "\ue963" or obj.name == "Enable video":
							obj.name = _("Enable video")
						elif first_child_name == "\ue964" or obj.name == "Disable video":
							obj.name = _("Disable video")
			except Exception as e:
				log.debugException(f"Swallowed exception: {e}")

		elif obj.role == Role.TOGGLEBUTTON:
			try:
				# Check if a toggle button is an answer option in a vote
				if "reactionTypeEmoji {" in obj.name:
					obj.name = re.sub(
						r"^(.+)reactionTypeEmoji.+\"(.)\".*",
						r"\g<1>\g<2>",
						obj.name,
						flags=re.S,
					)
				formatPollOption(obj)
			except Exception as e:
				log.debugException(f"Swallowed exception: {e}")

		# Resolve unlabeled elements
		if obj.name == "":
			resolveUnlabeledElement(obj)

	# ── Navigation Scripts ──────────────────────────────────────────────

	@script(
		# Translators: Description for the script that moves focus to the chat list.
		description=_("Move focus to topics, chats, contacts, or settings list"),
		gesture="kb:ALT+1",
	)
	def script_toChatList(self, gesture, arg=False):
		return self.nav_helper.script_toChatList(gesture, arg)

	@script(
		# Translators: Description for the script that moves focus to the last message.
		description=_("Move focus to the last message, profile, or settings"),
		gesture="kb:ALT+2",
	)
	def script_toLastMessage(self, gesture):
		return self.nav_helper.script_toLastMessage(gesture)

	@script(
		# Translators: Description for the script that moves focus to the unread messages label.
		description=_("Move focus to 'unread messages' label"),
		gesture="kb:ALT+U",
	)
	def script_goToTheLastUnreadMessage(self, gesture):
		return self.nav_helper.script_goToTheLastUnreadMessage(gesture)

	@script(
		# Translators: Description for the script that moves focus to chat folder tabs.
		description=_("Move focus to list of chat folders"),
		gesture="kb:ALT+4",
	)
	def script_to_tabs_folder(self, gesture):
		return self.nav_helper.script_to_tabs_folder(gesture)

	@script(
		# Translators: Description for the script that opens the navigation menu.
		description=_("Open navigation menu"),
		gesture="kb:ALT+M",
	)
	def script_showMenu(self, gesture):
		return self.nav_helper.script_showMenu(gesture)

	@script(
		# Translators: Description for the script that opens the current chat profile.
		description=_("Open current chat profile"),
		gesture="kb:alt+shift+P",
	)
	def script_openProfile(self, gesture):
		return self.nav_helper.script_openProfile(gesture)

	@script(
		# Translators: Description for the script that scrolls to the bottom of the chat.
		description=_("Scroll to the bottom of the chat"),
		gesture="kb:ALT+end",
	)
	def script_to_down(self, gesture):
		return self.nav_helper.script_to_down(gesture)

	@script(
		# Translators: Description for the script that focuses the search results list.
		description=_("Go to the list with search results"),
		gesture="kb:ALT+I",
	)
	def script_go_to_list_search_results(self, gesture):
		return self.nav_helper.script_go_to_list_search_results(gesture)

	@script(
		# Translators: Description for the script that goes to the next search result.
		description=_("Go to the next search result"),
		gesture="kb:F3",
	)
	def script_go_to_next_search_result(self, gesture):
		return self.nav_helper.script_go_to_next_search_result(gesture)

	@script(
		# Translators: Description for the script that goes to the previous search result.
		description=_("Go to the previous search result"),
		gesture="kb:shift+F3",
	)
	def script_go_to_previous_search_result(self, gesture):
		return self.nav_helper.script_go_to_previous_search_result(gesture)

	# ── Chat Scripts ────────────────────────────────────────────────────

	@script(
		# Translators: Description for the script that announces the chat name and status.
		description=_("Announce the name and status of an open chat"),
		gesture="kb:ALT+T",
	)
	def script_read_profile_name(self, gesture):
		return self.chats_helper.script_read_profile_name(gesture)

	@script(
		# Translators: Description for the script that opens the More Options menu in an open chat.
		description=_("Open more options menu in the active chat"),
		gesture="kb:ALT+shift+O",
	)
	def script_showMoreOptions(self, gesture):
		return self.chats_helper.script_showMoreOptions(gesture)

	# ── Message Scripts ─────────────────────────────────────────────────

	@script(
		# Translators: Description for the script that copies the focused message or link.
		description=_("Copy message text, or copy focused link URL"),
		gesture="kb:control+C",
	)
	def script_copyMessage(self, gesture):
		return self.msg_helper.script_copyMessage(gesture)

	@script(
		# Translators: Description for the script that opens the Instant View page.
		description=_("Open Instant View for the focused message"),
		gesture="kb:ALT+Q",
	)
	def script_instantView(self, gesture):
		return self.msg_helper.script_instantView(gesture)

	@script(
		# Translators: Description for the script that toggles focus between the edit field and messages.
		description=_("Toggle focus between message edit field and previous position"),
		gesture="kb:ALT+3",
	)
	def script_moveFocusToTextMessage(self, gesture):
		return self.msg_helper.script_moveFocusToTextMessage(gesture)

	@script(
		# Translators: Description for the script that clicks the Attach File button.
		description=_("Attach file or media to message"),
		gesture="kb:control+shift+A",
	)
	def script_add_files(self, gesture):
		return self.msg_helper.script_add_files(gesture)

	@script(
		# Translators: Description for the script that clicks the New Conversation button.
		description=_("Start a new chat"),
		gesture="kb:control+N",
	)
	def script_new_conversation(self, gesture):
		return self.msg_helper.script_new_conversation(gesture)

	@script(
		# Translators: Description for the script that deletes a message or chat.
		description=_("Delete a message or chat"),
		gestures=["kb:delete", "kb:shift+delete"],
	)
	def script_deletion(self, gesture):
		"""Unified deletion handler for both single-side (Delete) and two-sided (Shift+Delete) deletion."""
		self.isMessageSelectionMode = False
		is_shift = any("shift" in i.lower() for i in getattr(gesture, "identifiers", []))
		obj = api.getFocusObject()
		if self.ui_helper.is_message_object(obj):
			if not self.msg_helper.start_delete_message(isCompleteDeletion=is_shift):
				gesture.send()
		elif self.chats_helper.is_chat_item(obj):
			if not self.chats_helper.start_delete_chat(isCompleteDeletion=is_shift):
				gesture.send()
		else:
			gesture.send()

	@script(
		# Translators: Description for the script that switches the message or chat to selection mode.
		description=_("Switch to selection mode"),
		gesture="kb:control+space",
	)
	def script_selectMessage(self, gesture):
		obj = api.getFocusObject()
		if self.chats_helper.is_chat_item(obj):
			if not self.chats_helper.select_chat():
				gesture.send()
		elif self.ui_helper.is_message_object(obj):
			if not self.msg_helper.script_selectMessage(gesture):
				gesture.send()
		else:
			gesture.send()

	@script(
		# Translators: Description for the script that forwards the focused message.
		description=_("Forward message"),
		gesture="kb:ALT+F",
	)
	def script_forwardMessage(self, gesture):
		self.isMessageSelectionMode = False
		obj = api.getFocusObject()
		if self.ui_helper.is_message_object(obj):
			if not self.msg_helper.script_forwardMessage(gesture):
				gesture.send()
		else:
			gesture.send()

	@script(
		# Translators: Description for the script that marks a chat as read or unread.
		description=_("Mark focused chat as read"),
		gesture="kb:ALT+shift+R",
	)
	def script_readMessage(self, gesture):
		obj = api.getFocusObject()
		if self.chats_helper.is_chat_item(obj):
			if not self.chats_helper.read_chat():
				gesture.send()
		else:
			gesture.send()

	@script(
		# Translators: Description for the script that saves a file attachment.
		description=_("Save file as..."),
	)
	def script_save_file(self, gesture):
		obj = api.getFocusObject()
		if self.ui_helper.is_message_object(obj):
			if not self.msg_helper.script_save_file(gesture):
				gesture.send()
		else:
			gesture.send()

	@script(
		# Translators: Description for the script that pins or unpins a message/chat.
		description=_("Pin or unpin focused message or chat"),
		gesture="kb:control+P",
	)
	def script_attach(self, gesture):
		obj = api.getFocusObject()
		if self.chats_helper.is_chat_item(obj):
			if not self.chats_helper.pin_chat():
				gesture.send()
		elif self.ui_helper.is_message_object(obj):
			if not self.msg_helper.pin_message():
				gesture.send()
		else:
			gesture.send()

	@script(
		# Translators: Description for the script that copies broadcast RTMP data.
		description=_("Copy data for broadcasting to the clipboard"),
		gesture="kb:ALT+shift+L",
	)
	def script_copy_data_for_broadcast(self, gesture):
		return self.msg_helper.script_copy_data_for_broadcast(gesture)

	# ── Media Scripts ───────────────────────────────────────────────────

	@script(
		# Translators: Description for the script that cycles voice message playback speed.
		description=_("Change media playback speed"),
		gesture="kb:ALT+X",
	)
	def script_voiceMessageAcceleration(self, gesture):
		return self.media_helper.script_voiceMessageAcceleration(gesture)

	@script(
		# Translators: Description for the script that toggles focus to the voice slider.
		description=_("Toggle focus between audio playback slider and previous position"),
		gesture="kb:ALT+S",
	)
	def script_toggleVoiceSlider(self, gesture):
		return self.media_helper.script_toggleVoiceSlider(gesture)

	@script(
		# Translators: Description for the script that closes the audio player.
		description=_("Close audio player"),
		gesture="kb:ALT+E",
	)
	def script_closingVoiceMessage(self, gesture):
		return self.media_helper.script_closingVoiceMessage(gesture)

	@script(
		# Translators: Description for the script that plays/pauses the current voice message.
		description=_("Play or pause currently playing audio or voice message"),
		gesture="kb:ALT+P",
	)
	def script_pauseVoiceMessage(self, gesture):
		return self.media_helper.script_pauseVoiceMessage(gesture)

	@script(
		# Translators: Description for the script that plays or stops focused media.
		description=_("Play or stop focused media"),
		gesture="kb:space",
	)
	def script_actionMediaInMessage(self, gesture):
		obj = api.getFocusObject()
		if self.ui_helper.is_message_object(obj):
			return self.media_helper.script_actionMediaInMessage(gesture)
		if hasattr(obj, "script_activate_radio"):
			return obj.script_activate_radio(gesture)
		gesture.send()

	@script(
		# Translators: Description for the script that starts or stops voice message recording.
		description=_("Start or stop recording a voice message"),
		gesture="kb:control+R",
	)
	def script_recordingVoiceMessage(self, gesture):
		return self.media_helper.script_recordingVoiceMessage(gesture)

	@script(
		# Translators: Description for the script that cancels voice recording, message reply, or edit.
		description=_("Cancel voice recording, message reply, or edit"),
		gesture="kb:control+D",
	)
	def script_cancelVoiceMessageRecording(self, gesture):
		# Single press priority 1: Active voice message recording takes precedence
		if self.media_helper.is_voice_recording():
			self.media_helper.cancel_voice_recording(gesture)
			return

		# Single press priority 2: Active reply or editing session in the composer header
		if self.msg_helper.cancel_reply_or_edit():
			return

		# Fallback: Neither voice recording nor reply/edit active; pass gesture to Telegram
		gesture.send()

	@script(
		# Translators: Description for the script that converts a voice message to text.
		description=_("Convert voice message to text"),
		gesture="kb:NVDA+ALT+R",
	)
	def script_Recognize_voice_message(self, gesture):
		return self.media_helper.script_Recognize_voice_message(gesture)

	# ── Call Scripts ─────────────────────────────────────────────────────

	@script(
		# Translators: Description for the script that initiates a voice call or joins voice chat.
		description=_("Start voice call with contact, or join group voice chat"),
		gesture="kb:shift+alt+C",
	)
	def script_call(self, gesture):
		return self.call_helper.script_call(gesture)

	@script(
		# Translators: Description for the script that initiates a video call.
		description=_("Start video call"),
		gesture="kb:shift+alt+V",
	)
	def script_videoCall(self, gesture):
		return self.call_helper.script_videoCall(gesture)

	@script(
		# Translators: Description for the script that mutes/unmutes the microphone.
		description=_("Mute or unmute microphone in active call or voice chat"),
		gesture="kb:ALT+A",
	)
	def script_microphone(self, gesture):
		return self.call_helper.script_microphone(gesture)

	@script(
		# Translators: Description for the script that toggles the camera.
		description=_("Turn camera on or off in active video call"),
		gesture="kb:ALT+V",
	)
	def script_video(self, gesture):
		return self.call_helper.script_video(gesture)

	def script_callCancellation(self, gesture):
		"""End a call, decline an incoming call, or leave a voice chat."""
		return self.call_helper.script_callCancellation(gesture)

	# ── Utility Scripts ─────────────────────────────────────────────────


	@script(
		# Translators: Description for the script that toggles live chat automatic message reading.
		description=_("Toggle automatic live reading of incoming messages in the active chat"),
		gesture="kb:ALT+L",
	)
	def script_toggle_live_chat(self, gesture):
		"""Toggle real-time background announcement of incoming messages."""
		return self.msg_helper.script_toggle_live_chat(gesture)

	@script(
		# Translators: Description for the script that displays the shortcut list.
		description=_("Show a list of all UnigramAccess shortcuts"),
		gesture="kb:ALT+H",
	)
	def script_help(self, gesture):
		"""Parse readme.md and display all keyboard shortcuts in a popup window."""
		addon = addonHandler.getCodeAddon() or next(
			(item for item in list(addonHandler.getAvailableAddons()) if item.name in ("UnigramAccess", "unigramAccess")),
			None,
		)
		if not addon:
			message(_("Help document not found"))
			return

		readme_path = addon.getDocFilePath("readme.md")
		if not readme_path or not os.path.isfile(readme_path):
			message(_("Help document not found"))
			return

		with open(readme_path, "r", encoding="utf-8") as file:
			lines = file.readlines()

		parsedLines = []
		in_shortcuts = False
		for line in lines:
			stripped = line.strip()
			if stripped.startswith("## "):
				header = stripped[3:].strip().lower()
				if "shortcut" in header or "میانبر" in header:
					in_shortcuts = True
				else:
					in_shortcuts = False
			elif in_shortcuts:
				if stripped.startswith("### "):
					if parsedLines:
						parsedLines.append("")
					parsedLines.append(stripped.replace("### ", "") + ":")
				elif stripped.startswith("* **"):
					parsedLines.append(stripped.replace("* **", "").replace("**", ""))

		text = "\n".join(parsedLines).strip()
		if not text:
			message(_("Help document not found"))
			return

		TextWindow(text, _("List of shortcuts"), readOnly=True)

	@script(gesture="kb:escape")
	def script_action_escape_key(self, gesture):
		"""Handle Escape key: restore focus when exiting full-screen media viewer, delete dialog, or selection mode."""
		if self.isMessageSelectionMode:
			self.isMessageSelectionMode = False
			focus_obj = api.getFocusObject()
			target_msg = focus_obj if self.ui_helper.is_message_object(focus_obj) else self.saved_items.get("last focus object")
			self._selection_restore_target = target_msg
			gesture.send()
			core.callLater(150, self._restore_selection_focus, target_msg)
			return

		if self.isDelete and isinstance(self.isDelete, dict) and self.isDelete.get("state") == "awaiting_confirmation":
			self.isDelete["confirmed_dismissal"] = "escape"
			log.debug("Delete dialog: confirmed dismissal via Escape")

		focus_obj = api.getFocusObject()
		is_in_viewer = self.media_helper.is_media_popup_element(focus_obj)
		if is_in_viewer or (self.isMedia and isinstance(self.isMedia, dict) and not self.ui_helper.is_message_object(focus_obj)):
			target = (self.isMedia.get("initial_obj") if isinstance(self.isMedia, dict) else None) or self.saved_items.get("last focus object")
			if target:
				self.isMedia = {
					"initial_obj": target,
					"confirmed_dismissal": "escape",
				}
				log.debug("Media viewer: confirmed dismissal via Escape")
		else:
			self.isMedia = False

		gesture.send()
