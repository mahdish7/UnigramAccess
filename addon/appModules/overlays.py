# -*- coding:utf-8 -*-
# UI component classes for UnigramAccess addon

from NVDAObjects.UIA import ListItem
import winUser
import api
from controlTypes import Role, State
import scriptHandler
from scriptHandler import script
from keyboardHandler import KeyboardInputGesture
from ui import message
from threading import Timer
import editableText
import textInfos
import addonHandler

addonHandler.initTranslation()

from .data import *
from .text_window import *
from .cnf import conf, lang



class Audio_and_video_button:
	def script_enter(self, gesture):
		gesture.send()
		if self.UIAAutomationId == "Audio": new_name = self.next.name if self.next else self.name
		elif self.UIAAutomationId == "Video": new_name = _("Camera on") if self.firstChild.name == "\ue964" else _("Camera off") if self.firstChild.name == "\ue963" else self.name
		def spechState(): message(new_name)
		thr = Timer(.1, spechState).start()
	
	def initOverlayClass(self):
		self.bindGesture("kb:Enter", "enter")


class Message_list_item(ListItem):
	selected_media = -1
	media = None
	list_media = []
	UIAAutomationId = "Message_item"
	scriptCategory = "UnigramAccess"
	last_part_in_message = None
	index_last_part_in_message = 0

	@script(description=_("Announce the original message, the message that was replied to"), gesture="kb:leftArrow")
	def script_voice_answer(self, gesture):
		if self.selected_media > 0:
			self.script_next_media(gesture, True)
			return
		answer = next((item for item in self.children if item.UIAAutomationId == "Reply"), None)
		if answer and answer.name == "":
			answer = answer.firstChild
		if scriptHandler.getLastScriptRepeatCount() == 0 and answer: message(answer.name)
		elif scriptHandler.getLastScriptRepeatCount() == 1 and answer: answer.doAction()

	@script(description=_("Show message text in popup window"), gesture="kb:ALT+C")
	def script_show_text_message(self, gesture):
		text_message = next((item.name for item in self.children if item.UIAAutomationId in ("TextBlock", "Message", "Question")), "")
		recognized_text = next((item.name for item in self.children if item.UIAAutomationId == "RecognizedText"), "")
		if not text_message and not recognized_text:
			message(_("This message does not contain text"))
			return
		text_message = text_message.strip().replace("‍", "")
		recognized_text = recognized_text.strip().replace("‍", "")
		if text_message and recognized_text:
			text = "\n\n".join([text_message, recognized_text])
		else:
			text = text_message or recognized_text
		TextWindow(text, _("message text"), readOnly=False)

	@script(description=_("Open comments"), gesture="kb:control+ALT+C")
	def script_openComments(self, gesture):
		targetButton = next((item for item in reversed(self.children) if item.role == Role.LINK and item.UIAAutomationId == "Thread"), False)
		if targetButton:
			targetButton.doAction()
		else: message(_("Button to open comments not found"))

	@script(description=_("Edit message"), gesture="kb:backspace")
	def script_edit_message(self, gesture):
		self.appModule.activate_option_for_menu((icons_from_context_menu["edit"]), "Messages")
	
	@script(description=_("Reply to message"), gesture="kb:enter")
	def script_reply_to_message(self, gesture):
		self.appModule.activate_option_for_menu((icons_from_context_menu["reply"]), "Messages")

	def script_next_message(self, gesture):
		if self.parent.next: gesture.send()
		else: self.appModule.script_moveFocusToTextMessage(gesture)

	def script_next_media(self, gesture, revers=False):
		self.list_media = self.list_media or [item for item in self.children if item.role == Role.LISTITEM]
		obj = None
		if revers:
			self.selected_media -= 1
			obj = self.list_media[self.selected_media]
		elif self.selected_media < len(self.list_media)-1:
			self.selected_media += 1
			obj = self.list_media[self.selected_media]
		if not obj: return
		self.media = obj
		if obj.firstChild.UIAAutomationId == "Subtitle": name = _("Photo")
		elif obj.firstChild.UIAAutomationId == "Texture": name = _("Video")
		else:
			name = next((item.name for item in obj.children if item.UIAAutomationId in ("Title",)) , "Медіа")
		message(name)
		api.setNavigatorObject(obj.simpleFirstChild)

	@script(description=_("Announces the time a message was sent or received, as well as a list of reactions. Double-clicking toggles the announcement mode for this information."), gesture="kb:ALT+W")
	def script_toggle_sounding_message_information(self, gesture):
		if scriptHandler.getLastScriptRepeatCount() == 0:
			message(self.last_part_in_message)
		elif scriptHandler.getLastScriptRepeatCount() == 1:
			conf.set("announce_end_of_message", not conf.get("announce_end_of_message"))
			if conf.get("announce_end_of_message"): message(_("The display of message sending or receiving time and the list of installed emojis is enabled."))
			else: message(_("The display of message sending or receiving time and the list of installed emojis is  disabled."))

	def initOverlayClass(self):
		self.positionInfo = self.parent.positionInfo
		self.states.discard(State.SELECTABLE)
		keywords = keywordsInMessages.get(conf.get("lang"), keywordsInMessages["en"])
		self.keywords = keywords
		index = self.name.find(keywords[2])
		index = index if index != -1 else self.name.find(keywords[3])
		self.index_last_part_in_message = index
		self.last_part_in_message = self.name[index:]
		
		if conf.get("action_when_pressing_up_arrow_in_text_field") == "to_messages":
			self.bindGesture("kb:downArrow", "next_message")

	__gestures = {
		"kb:ALT+C": "show_text_message",
		"kb:rightArrow": "next_media",
		"kb:leftArrow": "voice_answer",
		"kb:backspace": "edit_message",
		"kb:enter": "reply_to_message",
	}


class SettingsPanelListItem:

	def script_activate_element(self, gesture):
		self.firstChild.doAction()
		self.appModule.script_toLastMessage(gesture)

	__gestures = {
		"kb:enter": "activate_element",
		"kb:space": "activate_element",
	}


class ExplanationCorrectAnswerInQuiz:
	def script_activate_element(self, gesture):
		gesture.send()
		elements = self.appModule.getElements()
		try: obj = elements[1].firstChild.firstChild.firstChild
		except: obj = None
		if not obj: return False
		TextWindow(obj.name, _("Explanation"), readOnly=False)

	__gestures = {
		"kb:enter": "activate_element",
		"kb:space": "activate_element",
	}


class EditableText(editableText.EditableText):

	def script_caret_moveByLine(self, gesture):
		if gesture.mainKeyName != "upArrow":
			return super().script_caret_moveByLine(gesture)
		info = None
		try:
			info = self.makeTextInfo(textInfos.POSITION_ALL)
		except Exception:
			pass
		if info and info.text == "":
			if conf.get("action_when_pressing_up_arrow_in_text_field") == "to_messages":
				self.appModule.script_toLastMessage(None)
			else: message("")
			return
		return super().script_caret_moveByLine(gesture)
