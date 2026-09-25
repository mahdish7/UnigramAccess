# -*- coding:utf-8 -*-
# UnigramAccess: Custom NVDAObject overlay classes for Unigram UI elements.

import api
from .unigram_logger import ulog as log
from controlTypes import Role, State
import editableText
from NVDAObjects.UIA import ListItem
import queueHandler
import scriptHandler
from scriptHandler import script
import textInfos
from threading import Timer
from ui import message

import addonHandler

addonHandler.initTranslation()

from .cnf import conf
from .data import keywordsInMessages
from .text_window import TextWindow
from .unigram_utils import isActivelyDownloading


class Media_download_button:
	"""Overlay class for media download and action buttons.

	Suppresses misleading/static percentage when idle (Bug 7).
	"""

	def _get_value(self):
		# Suppress misleading/static percentage when idle (Bug 7)
		if not isActivelyDownloading(getattr(self, "name", "")):
			return None
		return super()._get_value()

	value = property(_get_value)


class Audio_and_video_button:
	"""Overlay for call Audio/Video toggle buttons.

	Announces the new state after pressing Enter.
	"""

	def script_enter(self, gesture):
		gesture.send()

		def speakState():
			newName = None
			if self.UIAAutomationId == "Audio":
				first_child = getattr(self, "firstChild", None)
				child_name = getattr(first_child, "name", "") if first_child else ""
				if child_name == "\ue720":
					newName = _("Microphone turned on")
				elif child_name in ("\ue74f", "\uf781"):
					newName = _("Microphone turned off")
			elif self.UIAAutomationId == "Video":
				first_child = getattr(self, "firstChild", None)
				child_name = getattr(first_child, "name", "") if first_child else ""
				if child_name == "\ue964":
					newName = _("Camera turned on")
				elif child_name == "\ue963":
					newName = _("Camera turned off")

			if newName:
				queueHandler.queueFunction(queueHandler.eventQueue, message, newName)

		Timer(0.2, speakState).start()

	__gestures = {
		"kb:enter": "enter",
	}


class Message_list_item(ListItem):
	"""Overlay for message list items in the chat history.

	Provides scripts for replying, editing, viewing text, cycling media,
	announcing timestamps/reactions, and navigating to replied messages.
	"""

	selected_media = -1
	media = None
	list_media = []
	UIAAutomationId = "Message_item"
	scriptCategory = "UnigramAccess"
	last_part_in_message = None
	index_last_part_in_message = 0

	@script(
		# Translators: Description for the script that reads the replied-to message.
		description=_("Announce the original message, the message that was replied to"),
		gesture="kb:leftArrow",
	)
	def script_voice_answer(self, gesture):
		if self.selected_media > 0:
			self.script_next_media(gesture, True)
			return
		answer = next((item for item in self.children if item.UIAAutomationId == "Reply"), None)
		if answer and answer.name == "":
			answer = answer.firstChild
		if scriptHandler.getLastScriptRepeatCount() == 0 and answer:
			message(answer.name)
		elif scriptHandler.getLastScriptRepeatCount() == 1 and answer:
			answer.doAction()

	@script(
		# Translators: Description for the script that shows the message text in a popup window.
		description=_("Show message text in popup window"),
		gesture="kb:ALT+C",
	)
	def script_show_text_message(self, gesture):
		textMessage = next(
			(item.name for item in self.children if item.UIAAutomationId in ("TextBlock", "Message", "Question")),
			"",
		)
		recognizedText = next(
			(item.name for item in self.children if item.UIAAutomationId == "RecognizedText"),
			"",
		)
		if not textMessage and not recognizedText:
			message(_("This message does not contain text"))
			return
		textMessage = textMessage.strip().replace("\u200d", "")
		recognizedText = recognizedText.strip().replace("\u200d", "")
		if textMessage and recognizedText:
			text = "\n\n".join([textMessage, recognizedText])
		else:
			text = textMessage or recognizedText
		TextWindow(text, _("message text"), readOnly=False)

	@script(
		# Translators: Description for the script that opens the comments thread.
		description=_("Open comments"),
		gesture="kb:control+ALT+C",
	)
	def script_openComments(self, gesture):
		targetButton = next(
			(item for item in reversed(self.children) if item.role == Role.LINK and item.UIAAutomationId == "Thread"),
			False,
		)
		if targetButton:
			targetButton.doAction()
		else:
			message(_("Button to open comments not found"))

	@script(
		# Translators: Description for the script that opens the edit dialog for the focused message.
		description=_("Edit message"),
		gesture="kb:backspace",
	)
	def script_edit_message(self, gesture):
		if not self.appModule.msg_helper.activate_option_for_menu("edit"):
			gesture.send()

	@script(
		# Translators: Description for the script that replies to the focused message.
		description=_("Reply to message"),
		gesture="kb:enter",
	)
	def script_reply_to_message(self, gesture):
		if not self.appModule.msg_helper.activate_option_for_menu("reply"):
			gesture.send()

	@script(
		# Translators: Description for the script that navigates to the next media item in a message.
		description=_("Move to next media item in message"),
		gesture="kb:rightArrow",
	)
	def script_next_media(self, gesture, revers=False):
		self.list_media = self.list_media or [item for item in self.children if item.role == Role.LISTITEM]
		obj = None
		if revers:
			self.selected_media -= 1
			obj = self.list_media[self.selected_media]
		elif self.selected_media < len(self.list_media) - 1:
			self.selected_media += 1
			obj = self.list_media[self.selected_media]
		if not obj:
			return
		self.media = obj
		if obj.firstChild.UIAAutomationId == "Subtitle":
			name = _("Photo")
		elif obj.firstChild.UIAAutomationId == "Texture":
			name = _("Video")
		else:
			title_elem = next((item for item in obj.children if getattr(item, "UIAAutomationId", "") == "Title"), None)
			if title_elem and getattr(title_elem, "name", ""):
				name = title_elem.name.strip()
				trim_elem = next((item for item in obj.children if getattr(item, "UIAAutomationId", "") == "TitleTrim"), None)
				if trim_elem and getattr(trim_elem, "name", ""):
					name += trim_elem.name.strip()
			else:
				# Translators: Fallback label announced for unknown media items in a message.
				name = _("Media")
		message(name)
		api.setNavigatorObject(obj.simpleFirstChild)

	@script(
		# Translators: Description for the script that announces message time and reactions.
		description=_("Announce message timestamp and reactions. Press twice to toggle automatic announcement."),
		gesture="kb:ALT+W",
	)
	def script_toggle_sounding_message_information(self, gesture):
		if scriptHandler.getLastScriptRepeatCount() == 0:
			message(self.last_part_in_message)
		elif scriptHandler.getLastScriptRepeatCount() == 1:
			conf.set("announce_end_of_message", not conf.get("announce_end_of_message"))
			if conf.get("announce_end_of_message"):
				message(_("The display of message sending or receiving time and reactions is enabled."))
			else:
				message(_("The display of message sending or receiving time and reactions is disabled."))

	def initOverlayClass(self):
		self.positionInfo = self.parent.positionInfo
		self.states.discard(State.SELECTABLE)
		keywords = keywordsInMessages.get(conf.get("lang"), keywordsInMessages["en"])
		self.keywords = keywords
		index = -1
		if len(keywords) > 4 and keywords[4]:
			index = self.name.find(keywords[4])
			if index == -1 and "\u2068" in keywords[4]:
				index = self.name.find(keywords[4].replace("\u2068", ""))
		if index == -1 and len(keywords) > 5 and keywords[5]:
			index = self.name.find(keywords[5])
			if index == -1 and "\u2068" in keywords[5]:
				index = self.name.find(keywords[5].replace("\u2068", ""))
		if index == -1:
			index = self.name.find(keywords[2])
		if index == -1:
			index = self.name.find(keywords[3])
		self.index_last_part_in_message = index
		self.last_part_in_message = self.name[index:] if index != -1 else ""

	__gestures = {
		"kb:ALT+C": "show_text_message",
		"kb:rightArrow": "next_media",
		"kb:leftArrow": "voice_answer",
		"kb:backspace": "edit_message",
		"kb:enter": "reply_to_message",
	}


class SettingsPanelListItem:
	"""Overlay for navigation panel list items.

	Activates the item and jumps focus to the settings right-side detail panel.
	"""

	def script_activate_element(self, gesture):
		self.firstChild.doAction()
		if getattr(self.appModule, "settings_helper", None):
			self.appModule.settings_helper.to_detail_panel()
		else:
			self.appModule.nav_helper.script_toLastMessage(gesture)

	__gestures = {
		"kb:enter": "activate_element",
		"kb:space": "activate_element",
	}


class SettingsRadioListItem:
	"""Overlay for settings list items wrapping an inner RadioButton (e.g. Proxy, Language, etc.).

	Reports radio button role and checked state, and activates the inner radio on Space.
	"""

	def _get_role(self):
		return Role.RADIOBUTTON

	role = property(_get_role)

	def _get_states(self):
		states = super()._get_states()
		states.add(State.CHECKABLE)
		child = getattr(self, "firstChild", None)
		if child and getattr(child, "role", None) == Role.RADIOBUTTON:
			if State.CHECKED in getattr(child, "states", set()):
				states.add(State.CHECKED)
			else:
				states.discard(State.CHECKED)
		return states

	states = property(_get_states)

	def script_activate_radio(self, gesture):
		child = getattr(self, "firstChild", None)
		if child and getattr(child, "role", None) == Role.RADIOBUTTON:
			child.doAction()
			self.setFocus()
		else:
			self.doAction()

	__gestures = {
		"kb:space": "activate_radio",
	}






class EditableText(editableText.EditableText):
	"""Overlay for the chat message compose field.

	Overrides up-arrow behavior: when the text field is empty, either jumps to
	the last message or blocks the key, based on user configuration.
	"""

	def script_caret_moveByLine(self, gesture):
		if gesture.mainKeyName != "upArrow":
			return super().script_caret_moveByLine(gesture)
		info = None
		try:
			info = self.makeTextInfo(textInfos.POSITION_ALL)
		except Exception as e:
			log.debugException(f"Swallowed exception: {e}")
		if info and info.text == "":
			action = conf.get("action_when_pressing_up_arrow_in_text_field")
			if action == "to_messages":
				self.appModule.nav_helper.script_toLastMessage(None)
				return
			elif action == "do_nothing":
				return
			return super().script_caret_moveByLine(gesture)
		return super().script_caret_moveByLine(gesture)
