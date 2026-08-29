# -*- coding:utf-8 -*-
import addonHandler
addonHandler.initTranslation()
from controlTypes import Role, State
from ui import message
import api
import speech
from nvwave import playWaveFile
import os
from .data import *
from .text_window import *
from .cnf import conf

baseDir = os.path.join(os.path.dirname(__file__), "media")

class UnigramMessages:
	def __init__(self, appModule):
		self.appModule = appModule

	def script_instantView(self, gesture):
		obj = api.getFocusObject()
		if not self.appModule.ui_helper.is_message_object(obj): return
		targetButton = next((item.next for item in obj.children if item.UIAAutomationId == "TextBlock" and item.next and item.next.lastChild and item.next.lastChild.UIAAutomationId == "Button"), False)
		if targetButton:
			targetButton.doAction()
			targetList = next((item for item in self.appModule.ui_helper.getElements() if item.role == Role.LIST and item.UIAAutomationId == "ScrollingHost"), False)
			if targetList:
				item = next((item for item in targetList.children if item.name != ""), None)
				if item: item.setFocus()
		else: message(_("Button not found"))

	def script_copyMessage(self, gesture):
		gesture.send()
		obj = api.getFocusObject()
		if obj.parent.UIAAutomationId in ("Message", "TextBlock"):
			textMessage = obj.name
			mes = _("Link copied")
		else: return
		if textMessage:
			api.copyToClip(textMessage.strip())
			message(mes)
		else: message(_("This message does not contain text"))

	def _script_show_text_message(self, gesture):
		obj = api.getFocusObject()
		if not self.appModule.ui_helper.is_message_object(obj): return False
		textMessage = next((item.name for item in obj.children if item.UIAAutomationId in ("TextBlock", "Message", "Question")), False)
		if textMessage: TextWindow(textMessage.strip(), _("message text"), readOnly=False)
		else: message(_("This message does not contain text"))

	def script_moveFocusToTextMessage(self, gesture):
		obj = api.getFocusObject()
		lastFocusObject = self.appModule.saved_items.get("last focus object")
		if (obj.role == Role.EDITABLETEXT and obj.UIAAutomationId == "TextField") or (obj.role == Role.BUTTON and obj.UIAAutomationId == "ButtonAction"):
			if lastFocusObject and lastFocusObject.location: lastFocusObject.setFocus()
			return
		targetButton = self.appModule.saved_items.get("message box")
		if not targetButton or not targetButton.location or not targetButton.location.width:
			targetButton = False
			for item in reversed(self.appModule.ui_helper.getElements()):
				if item.role == Role.EDITABLETEXT and item.UIAAutomationId == "TextField":
					targetButton = item
					self.appModule.saved_items.save("message box", item)
					break
		if targetButton: targetButton.setFocus()
		elif lastFocusObject and lastFocusObject.location : lastFocusObject.setFocus()
		else: message(_("Message input field not found"))

	def script_add_files(self, gesture):
		button = next((item for item in self.appModule.ui_helper.getElements() if item.UIAAutomationId and item.UIAAutomationId == "ButtonAttach"), None)
		if button: button.doAction()
		else: message(_("Button not found"))

	def script_new_conversation(self, gesture):
		button = next((item for item in self.appModule.ui_helper.getElements() if item.UIAAutomationId and item.UIAAutomationId == "ComposeButton"), None)
		if button: button.doAction()
		else: message(_("Button not found"))

	def script_showMoreOptions(self, gesture):
		labels_for_button = labels_for_button_more_options.get(conf.get("lang"), labels_for_button_more_options["en"])
		targetButton = next((item for item in self.appModule.ui_helper.getElements() if item.role == Role.BUTTON and (item.UIAAutomationId in ("Options", "Menu", "Settings") or item.name in labels_for_button) ), False)
		if targetButton: targetButton.doAction()
		else: message(_("Button not found"))

	def script_copy_data_for_broadcast(self, gesture):
		dialog = next((item for item in self.appModule.ui_helper.getElements() if item.role == Role.DIALOG), False)
		if not dialog:
			message(_("Broadcast window not found"))
			return False
		data_area = next((item for item in dialog.children if item.role == Role.PANE and item.UIAAutomationId == "ContentScrollViewer"), False)
		if not data_area:
			message(_("Broadcast window not found"))
			return False
		url = next((item for item in data_area.children if item.UIAAutomationId == "Presenter"), False)
		if not url or not url.next or not url.next.next:
			message(_("Data not found"))
			return False
		key = url.next.next
		url_name = url.previous.name if url.previous else "URL"
		key_name = key.previous.name if key.previous else "Key"
		result_message = f"{url_name}: {url.name}\n{key_name}: {key.name}"
		api.copyToClip(result_message.strip())
		text_message = _("%url and %key copied to clipboard")
		text_message = text_message.replace("%url", url_name)
		text_message = text_message.replace("%key", key_name)
		message(text_message)

	def script_set_reaction(self, gesture):
		obj = api.getFocusObject()
		if not self.appModule.ui_helper.is_message_object(obj): return
		self.appModule.keys["Applications"].send()
		try: index = int(gesture.mainKeyName[-1])
		except (AttributeError, ValueError): return
		self.appModule.is_set_reaction = index

	def script_reviewRecentMessage(self, gesture):
		try: index = int(gesture.mainKeyName[-1])
		except (AttributeError, ValueError): return
		if index == 0: index = 10
		obj = self.appModule.ui_helper.getMessagesElement()
		if not obj:
			message(_("No open chat"))
			return
		target = obj.lastChild
		if not target:
			message(_("This chat is empty"))
			return
		i = 0
		while target:
			child = target.firstChild
			if child.role not in (Role.BUTTON, Role.GROUPING):
				i += 1
				if i == index:
					message(self.appModule.action_message_focus(target))
					api.setNavigatorObject(target)
					break
			target = target.previous
		if i < index:
			message(_("This chat is empty"))
			return

	def script_copy(self, gesture):
		self.activate_option_for_menu((icons_from_context_menu["copy"]), "Messages")

	def script_selectMessage(self, gesture):
		self.activate_option_for_menu((icons_from_context_menu["select"]), "Messages")

	def script_forwardMessage(self, gesture):
		self.activate_option_for_menu((icons_from_context_menu["forward"]), "Messages")

	def script_readMessage(self, gesture):
		self.activate_option_for_menu((icons_from_context_menu["read"], icons_from_context_menu["unread"]), "ChatsList")

	def script_save_file(self, gesture):
		self.activate_option_for_menu((icons_from_context_menu["save_as"]), "Messages")

	def script_attach(self, gesture):
		self.activate_option_for_menu((icons_from_context_menu["attach"], icons_from_context_menu["unpin"]))

	def activate_option_for_menu(self, option, list_name=False):
		if self.appModule.execute_context_menu_option: return False
		obj = api.getFocusObject()
		if list_name == "Messages" and not self.appModule.ui_helper.is_message_object(obj): return False
		elif list_name == "ChatsList" and obj.parent.UIAAutomationId and obj.parent.UIAAutomationId != list_name: return False
		elif not list_name and (not self.appModule.ui_helper.is_message_object(obj) and obj.parent.UIAAutomationId and obj.parent.UIAAutomationId != "ChatsList"): return
		self.appModule.execute_context_menu_option = option
		self.appModule.keys["Applications"].send()

	def startDeleteMessage(self, isCompleteDeletion = False):
		obj = api.getFocusObject()
		if self.appModule.ui_helper.is_message_object(obj) or obj.parent.UIAAutomationId == "ChatsList":
			self.appModule.isDelete = {"isCompleteDeletion": isCompleteDeletion, "elements": [], "message": "", "list": "", "state": 0}
			if self.appModule.ui_helper.is_message_object(obj):
				self.appModule.isDelete["list"] = "messages"
				if self.appModule.isDelete["isCompleteDeletion"]: self.appModule.isDelete["message"] = _("Message deleted on both sides")
				else: self.appModule.isDelete["message"] = _("Message deleted")
			elif obj.parent.UIAAutomationId == "ChatsList":
				self.appModule.isDelete["list"] = "chats"
				if obj.children[1].name == "": self.appModule.isDelete["message"] = _("You left the group")
				elif obj.children[1].name == "": self.appModule.isDelete["message"] = _("You left the channel")
				elif obj.children[1].name == "" and self.appModule.isDelete["isCompleteDeletion"]: self.appModule.isDelete["message"] = _("Bot removed and blocked")
				elif obj.children[1].name == "": self.appModule.isDelete["message"] = _("Bot removed")
				elif self.appModule.isDelete["isCompleteDeletion"]: self.appModule.isDelete["message"] = _("Chat deleted on both sides")
				else: self.appModule.isDelete["message"] = _("Chat deleted")
			if conf.get("audioPlaybackWhenDeleted"): self.appModule.isDelete["message"] = "audio"
			if obj.parent.role == Role.LISTITEM: obj = obj.parent
			if obj.next and obj.next.role == Role.LISTITEM and obj.next.childCount > 1: self.appModule.isDelete["elements"].append(obj.next.firstChild)
			if obj.previous and obj.previous.role == Role.LISTITEM and obj.previous.childCount > 1: self.appModule.isDelete["elements"].append(obj.previous.firstChild)
			if obj.previous and obj.previous.previous and obj.previous.previous.role == Role.LISTITEM and obj.previous.previous.childCount > 1: self.appModule.isDelete["elements"].append(obj.previous.previous.firstChild)
			if obj.next and obj.next.next and obj.next.next.role == Role.LISTITEM and obj.next.next.childCount > 1: self.appModule.isDelete["elements"].append(obj.next.next.firstChild)
			self.appModule.keys["Applications"].send()
			return True
		else: return False

	def deleteMessageAndChat(self, obj):
		if not conf.get("confirmation_at_deletion"): speech.cancelSpeech()
		if self.appModule.isDelete["state"] == 0 and obj.role == Role.MENUITEM:
			for item in obj.parent.children:
				if item.firstChild.name == icons_from_context_menu["delete"]:
					self.appModule.isDelete["state"] = 1
					item.doAction()
					if conf.get("confirmation_at_deletion"): self.appModule.isDelete = False
					return
			self.appModule.isDelete = False
			self.appModule.keys["escape"].send()
		elif self.appModule.isDelete["state"] == 1 and obj.role in (Role.CHECKBOX, Role.BUTTON):
			targetButton = next((x for x in self.appModule.isDelete["elements"] if x.location and x.location.width), False)
			if obj.role == Role.CHECKBOX:
				if obj.UIAAutomationId in ("CheckBox", "RevokeCheck") and ((self.appModule.isDelete["isCompleteDeletion"] and State.CHECKED not in obj.states) or (not self.appModule.isDelete["isCompleteDeletion"] and State.CHECKED in obj.states)): obj.doAction()
				obj.parent.lastChild.previous.doAction()
			elif obj.role == Role.BUTTON:
				obj.doAction()
			if targetButton: targetButton.setFocus()
			elif self.appModule.isDelete["list"] == "messages": self.appModule.nav_helper.script_toLastMessage(False)
			elif self.appModule.isDelete["list"] == "chats": self.appModule.nav_helper.script_toChatList(False)
			self.appModule.isDelete["state"] = 2
		elif self.appModule.isDelete["state"] != 1:
			if self.appModule.isDelete["message"] == "audio": playWaveFile(os.path.join(baseDir, "delete.wav"))
			else: message(self.appModule.isDelete["message"])
			if self.appModule.isDelete["list"] == "messages": message(obj.name)
			elif self.appModule.isDelete["list"] == "chats": message(self.appModule.actionChatElementInFocus(obj))
			self.appModule.isDelete = False

	def script_deletion(self, gesture):
		if not self.appModule.isDelete and not self.startDeleteMessage(False): gesture.send()

	def script_completeDeletion(self, gesture):
		if not self.appModule.isDelete and not self.startDeleteMessage(True): gesture.send()
