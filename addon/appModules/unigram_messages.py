# -*- coding:utf-8 -*-
# UnigramAccess: Message interaction logic (copy, delete, forward, reply, etc.).

import os

import api
from controlTypes import Role, State
from nvwave import playWaveFile
import speech
from ui import message

import addonHandler

addonHandler.initTranslation()

from .cnf import conf
from .data import composer_header_cancel_types, icons_from_context_menu
from .unigram_formatting import formatChatElementOnFocus
from .unigram_logger import ulog as log
from .unigram_utils import BASE_DIR, CACHED_KEYS


class UnigramMessages:
	"""Handles message-level interactions in Unigram.

	Manages context menu actions, clipboard operations, deletion state machine,
	broadcast data extraction, and message input field navigation.
	"""

	def __init__(self, appModule):
		self.appModule = appModule

	def script_instantView(self, gesture):
		"""Open Telegram Instant View for the focused message."""
		obj = api.getFocusObject()
		if not self.appModule.ui_helper.is_message_object(obj):
			return
		targetButton = next(
			(
				item.next
				for item in obj.children
				if item.UIAAutomationId == "TextBlock"
				and item.next
				and item.next.lastChild
				and item.next.lastChild.UIAAutomationId == "Button"
			),
			False,
		)
		if targetButton:
			targetButton.doAction()
			targetList = next(
				(item for item in self.appModule.ui_helper.getElements() if item.role == Role.LIST and item.UIAAutomationId == "ScrollingHost"),
				False,
			)
			if targetList:
				item = next((item for item in targetList.children if item.name != ""), None)
				if item:
					item.setFocus()
		else:
			message(_("Button not found"))

	def script_copyMessage(self, gesture):
		"""Copy message text or focused link to clipboard."""
		gesture.send()
		obj = api.getFocusObject()
		if obj.parent.UIAAutomationId in ("Message", "TextBlock"):
			textMessage = obj.name
			mes = _("Link copied")
		else:
			return
		if textMessage:
			api.copyToClip(textMessage.strip())
			message(mes)
		else:
			message(_("This message does not contain text"))

	def script_moveFocusToTextMessage(self, gesture):
		"""Toggle focus between the message input field and previous focus object."""
		obj = api.getFocusObject()
		lastFocusObject = self.appModule.saved_items.get("last focus object")
		if (obj.role == Role.EDITABLETEXT and obj.UIAAutomationId == "TextField") or (
			obj.role == Role.BUTTON and obj.UIAAutomationId == "ButtonAction"
		):
			if lastFocusObject and lastFocusObject.location:
				lastFocusObject.setFocus()
			return
		targetButton = self.appModule.saved_items.get("message box")
		if not targetButton or not targetButton.location or not targetButton.location.width:
			targetButton = False
			for item in reversed(self.appModule.ui_helper.getElements()):
				if item.role == Role.EDITABLETEXT and item.UIAAutomationId == "TextField":
					targetButton = item
					self.appModule.saved_items.save("message box", item)
					break
		if targetButton:
			targetButton.setFocus()
		elif lastFocusObject and lastFocusObject.location:
			lastFocusObject.setFocus()
		else:
			message(_("Message input field not found"))

	def script_add_files(self, gesture):
		"""Click the Attach File button."""
		button = next(
			(item for item in self.appModule.ui_helper.getElements() if item.UIAAutomationId and item.UIAAutomationId == "ButtonAttach"),
			None,
		)
		if button:
			button.doAction()
		else:
			message(_("Button not found"))

	def script_new_conversation(self, gesture):
		"""Click the New Conversation button."""
		button = next(
			(item for item in self.appModule.ui_helper.getElements() if item.UIAAutomationId and item.UIAAutomationId == "ComposeButton"),
			None,
		)
		if button:
			button.doAction()
		else:
			message(_("Button not found"))

	# TODO: Unimplemented / Inactive feature.
	# Not currently mapped to any gesture or called from AppModule.
	# Requires 'labels_for_button_more_options' to be defined in data.py to function.
	def script_showMoreOptions(self, gesture):
		"""Open the More Options menu in an open chat."""
		from .data import labels_for_button_more_options

		labelsForButton = labels_for_button_more_options.get(conf.get("lang"), labels_for_button_more_options["en"])
		targetButton = next(
			(
				item
				for item in self.appModule.ui_helper.getElements()
				if item.role == Role.BUTTON
				and (item.UIAAutomationId in ("Options", "Menu", "Settings") or item.name in labelsForButton)
			),
			False,
		)
		if targetButton:
			targetButton.doAction()
		else:
			message(_("Button not found"))

	def script_copy_data_for_broadcast(self, gesture):
		"""Extract and copy streaming RTMP URL and stream key to clipboard."""
		dialog = next(
			(item for item in self.appModule.ui_helper.getElements() if item.role == Role.DIALOG),
			False,
		)
		if not dialog:
			message(_("Broadcast window not found"))
			return False
		dataArea = next(
			(item for item in dialog.children if item.role == Role.PANE and item.UIAAutomationId == "ContentScrollViewer"),
			False,
		)
		if not dataArea:
			message(_("Broadcast window not found"))
			return False
		url = next(
			(item for item in dataArea.children if item.UIAAutomationId == "Presenter"),
			False,
		)
		if not url or not url.next or not url.next.next:
			message(_("Data not found"))
			return False
		key = url.next.next
		urlName = url.previous.name if url.previous else "URL"
		keyName = key.previous.name if key.previous else "Key"
		resultMessage = f"{urlName}: {url.name}\n{keyName}: {key.name}"
		api.copyToClip(resultMessage.strip())
		textMessage = _("%url and %key copied to clipboard")
		textMessage = textMessage.replace("%url", urlName)
		textMessage = textMessage.replace("%key", keyName)
		message(textMessage)

	# TODO: Incomplete / Reserved feature.
	# Sets 'isSetReaction' on appModule, but the focus handler in AppModule
	# does not currently consume or navigate reaction buttons. Not bound to any gesture.
	def script_set_reaction(self, gesture):
		"""Trigger a context menu reaction selection."""
		obj = api.getFocusObject()
		if not self.appModule.ui_helper.is_message_object(obj):
			return
		CACHED_KEYS["Applications"].send()
		try:
			index = int(gesture.mainKeyName[-1])
		except (AttributeError, ValueError):
			return
		self.appModule.isSetReaction = index

	def script_selectMessage(self, gesture):
		"""Switch message to selection mode via context menu."""
		self.activate_option_for_menu((icons_from_context_menu["select"]), "Messages")

	def script_forwardMessage(self, gesture):
		"""Forward message via context menu."""
		self.activate_option_for_menu((icons_from_context_menu["forward"]), "Messages")

	def script_readMessage(self, gesture):
		"""Mark chat as read/unread via context menu."""
		self.activate_option_for_menu(
			(icons_from_context_menu["read"], icons_from_context_menu["unread"]),
			"ChatsList",
		)

	def script_save_file(self, gesture):
		"""Save attached file via context menu."""
		self.activate_option_for_menu((icons_from_context_menu["save_as"]), "Messages")

	def script_attach(self, gesture):
		"""Pin/unpin message or chat via context menu."""
		self.activate_option_for_menu(
			(icons_from_context_menu["attach"], icons_from_context_menu["unpin"]),
		)

	def activate_option_for_menu(self, option, listName=False):
		"""Open context menu and automatically select a specific option.

		Sets the execute_context_menu_option flag which event_gainFocus
		picks up when the context menu appears.
		"""
		if self.appModule.executeContextMenuOption:
			return False
		obj = api.getFocusObject()
		if listName == "Messages" and not self.appModule.ui_helper.is_message_object(obj):
			return False
		elif listName == "ChatsList" and obj.parent.UIAAutomationId and obj.parent.UIAAutomationId != listName:
			return False
		elif not listName and (
			not self.appModule.ui_helper.is_message_object(obj)
			and obj.parent.UIAAutomationId
			and obj.parent.UIAAutomationId != "ChatsList"
		):
			return
		self.appModule.executeContextMenuOption = option
		CACHED_KEYS["Applications"].send()

	def startDeleteMessage(self, isCompleteDeletion=False):
		"""Begin the multi-step message/chat deletion flow.

		Saves adjacent elements for focus restoration after deletion,
		then opens the context menu to find the delete option.
		"""
		obj = api.getFocusObject()
		if self.appModule.ui_helper.is_message_object(obj) or obj.parent.UIAAutomationId == "ChatsList":
			self.appModule.isDelete = {
				"isCompleteDeletion": isCompleteDeletion,
				"elements": [],
				"message": "",
				"list": "",
				"state": 0,
			}
			if self.appModule.ui_helper.is_message_object(obj):
				self.appModule.isDelete["list"] = "messages"
				if isCompleteDeletion:
					self.appModule.isDelete["message"] = _("Message deleted on both sides")
				else:
					self.appModule.isDelete["message"] = _("Message deleted")
			elif obj.parent.UIAAutomationId == "ChatsList":
				self.appModule.isDelete["list"] = "chats"
				if obj.children[1].name == "":
					self.appModule.isDelete["message"] = _("You left the group")
				elif obj.children[1].name == "":
					self.appModule.isDelete["message"] = _("You left the channel")
				elif obj.children[1].name == "" and isCompleteDeletion:
					self.appModule.isDelete["message"] = _("Bot removed and blocked")
				elif obj.children[1].name == "":
					self.appModule.isDelete["message"] = _("Bot removed")
				elif isCompleteDeletion:
					self.appModule.isDelete["message"] = _("Chat deleted on both sides")
				else:
					self.appModule.isDelete["message"] = _("Chat deleted")
			if conf.get("audioPlaybackWhenDeleted"):
				self.appModule.isDelete["message"] = "audio"
			if obj.parent.role == Role.LISTITEM:
				obj = obj.parent
			if obj.next and obj.next.role == Role.LISTITEM and obj.next.childCount > 1:
				self.appModule.isDelete["elements"].append(obj.next.firstChild)
			if obj.previous and obj.previous.role == Role.LISTITEM and obj.previous.childCount > 1:
				self.appModule.isDelete["elements"].append(obj.previous.firstChild)
			if obj.previous and obj.previous.previous and obj.previous.previous.role == Role.LISTITEM and obj.previous.previous.childCount > 1:
				self.appModule.isDelete["elements"].append(obj.previous.previous.firstChild)
			if obj.next and obj.next.next and obj.next.next.role == Role.LISTITEM and obj.next.next.childCount > 1:
				self.appModule.isDelete["elements"].append(obj.next.next.firstChild)
			CACHED_KEYS["Applications"].send()
			return True
		else:
			return False

	def deleteMessageAndChat(self, obj):
		"""Execute the next step in the deletion state machine.

		State 0: Find and click delete in context menu.
		State 1: Handle confirmation dialog (checkbox + button).
		State 2+: Announce result and restore focus.
		"""
		if not conf.get("confirmation_at_deletion"):
			speech.cancelSpeech()
		if self.appModule.isDelete["state"] == 0 and obj.role == Role.MENUITEM:
			for item in obj.parent.children:
				if item.firstChild.name == icons_from_context_menu["delete"]:
					self.appModule.isDelete["state"] = 1
					item.doAction()
					if conf.get("confirmation_at_deletion"):
						self.appModule.isDelete = False
					return
			self.appModule.isDelete = False
			CACHED_KEYS["escape"].send()
		elif self.appModule.isDelete["state"] == 1 and obj.role in (Role.CHECKBOX, Role.BUTTON):
			targetButton = next(
				(x for x in self.appModule.isDelete["elements"] if x.location and x.location.width),
				False,
			)
			if obj.role == Role.CHECKBOX:
				if obj.UIAAutomationId in ("CheckBox", "RevokeCheck") and (
					(self.appModule.isDelete["isCompleteDeletion"] and State.CHECKED not in obj.states)
					or (not self.appModule.isDelete["isCompleteDeletion"] and State.CHECKED in obj.states)
				):
					obj.doAction()
				obj.parent.lastChild.previous.doAction()
			elif obj.role == Role.BUTTON:
				obj.doAction()
			if targetButton:
				targetButton.setFocus()
			elif self.appModule.isDelete["list"] == "messages":
				self.appModule.nav_helper.script_toLastMessage(False)
			elif self.appModule.isDelete["list"] == "chats":
				self.appModule.nav_helper.script_toChatList(False)
			self.appModule.isDelete["state"] = 2
		elif self.appModule.isDelete["state"] != 1:
			if self.appModule.isDelete["message"] == "audio":
				playWaveFile(os.path.join(BASE_DIR, "delete.wav"))
			else:
				message(self.appModule.isDelete["message"])
			if self.appModule.isDelete["list"] == "messages":
				message(obj.name)
			elif self.appModule.isDelete["list"] == "chats":
				message(formatChatElementOnFocus(obj))
			self.appModule.isDelete = False

	def script_deletion(self, gesture):
		"""Delete current message or chat (single-side)."""
		if not self.appModule.isDelete and not self.startDeleteMessage(False):
			gesture.send()

	def script_completeDeletion(self, gesture):
		"""Delete current message or chat from both sides."""
		if not self.appModule.isDelete and not self.startDeleteMessage(True):
			gesture.send()

	def get_composer_cancel_button(self):
		"""Find the Cancel button in the composer header (reply or edit mode)."""
		for item in reversed(self.appModule.ui_helper.getElements()):
			if item.role == Role.BUTTON and getattr(item, "UIAAutomationId", None) == "ComposerHeaderCancel":
				return item
		return None

	def cancel_reply_or_edit(self):
		"""Cancel active message reply or editing session.

		Returns True if a composer cancel action was performed, False otherwise.
		"""
		btn = self.get_composer_cancel_button()
		if not btn:
			return False

		last_focus = api.getFocusObject()
		btn_name = (getattr(btn, "name", None) or "").strip().lower()
		reply_kws = [kw for kws in composer_header_cancel_types.get("reply", {}).values() for kw in kws]
		edit_kws = [kw for kws in composer_header_cancel_types.get("edit", {}).values() for kw in kws]
		is_reply = any(kw in btn_name for kw in reply_kws)
		is_edit = any(kw in btn_name for kw in edit_kws)

		try:
			btn.doAction()
		except Exception as e:
			log.debug(f"Failed to invoke ComposerHeaderCancel: {e}")
			return False

		if last_focus:
			try:
				last_focus.setFocus()
			except Exception:
				pass

		if is_reply:
			message(_("Reply canceled"))
		elif is_edit:
			message(_("Edit canceled"))
		return True
