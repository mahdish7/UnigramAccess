# -*- coding:utf-8 -*-
# UnigramAccess: Message interaction logic (copy, delete, forward, reply, etc.).

import os

import api
from controlTypes import Role, State
import core
from keyboardHandler import KeyboardInputGesture
from nvwave import playWaveFile
import queueHandler
import speech
from ui import message

import addonHandler

addonHandler.initTranslation()

from .cnf import conf
from .data import composer_header_cancel_types, icons_from_context_menu, keywordsInMessages
from .unigram_logger import ulog as log
from .unigram_utils import BASE_DIR, CACHED_KEYS


class Chat_update:
	"""Polling loop that tracks new incoming messages in the active chat.

	When live chat mode is enabled (ALT+L), monitors message count changes
	and automatically announces new received messages.
	Uses core.callLater with a 300 ms interval.
	"""

	active = False
	pause = False
	interval = 0.3
	app = False

	@classmethod
	def tick(cls):
		if not cls.active or cls.pause:
			return
		try:
			lastMessage = cls.app.ui_helper.getMessagesElement().lastChild
		except Exception:
			lastMessage = False
		if not lastMessage or not lastMessage.isInForeground:
			cls.pause = True
			return False
		# First item = chat name where the last message was recorded
		# Second item = the message index
		lastSavedMessage = cls.app.saved_items.get("last message") or ("", "")
		# If there is a problem getting the message index, terminate and retry
		try:
			lastMessage.positionInfo["indexInGroup"]
			lastMessage.positionInfo["similarItemsInGroup"]
		except Exception:
			core.callLater(int(cls.interval * 1000), cls.tick)
			return
		if (
			lastMessage.positionInfo["indexInGroup"] != lastSavedMessage[1]
			and lastMessage.positionInfo["indexInGroup"] == lastMessage.positionInfo["similarItemsInGroup"]
		):
			try:
				title = cls.app.saved_items.get("profile name").firstChild.name
			except Exception:
				title = False
			keywords = keywordsInMessages.get(conf.get("lang"), keywordsInMessages["en"])
			if ((title == lastSavedMessage[0]) or not title) and keywords[3] in lastMessage.name[-60:]:
				from .unigram_formatting import formatMessageOnFocus

				text = formatMessageOnFocus(lastMessage.firstChild, cls.app.saved_items)
				queueHandler.queueFunction(queueHandler.eventQueue, message, text)
			try:
				newMessage = (title, lastMessage.positionInfo["indexInGroup"])
				cls.app.saved_items.save("last message", newMessage)
			except Exception:
				pass
		core.callLater(int(cls.interval * 1000), cls.tick)

	@classmethod
	def toggle(cls, app=False):
		if not conf.get("automatically announce new messages") or not app:
			cls.active = True
			conf.set("automatically announce new messages", True)
			cls.app = app
			core.callLater(int(cls.interval * 1000), cls.tick)
			return True
		else:
			cls.active = False
			conf.set("automatically announce new messages", False)
			return False

	@classmethod
	def restore(cls, app=False):
		cls.pause = False
		cls.active = True
		cls.app = app
		cls.app.saved_items.save("last message", None)
		core.callLater(int(cls.interval * 1000), cls.tick)


class UnigramMessages:
	"""Handles message-level interactions in Unigram.

	Manages context menu actions, clipboard operations, deletion state machine,
	broadcast data extraction, and message input field navigation.
	"""

	def __init__(self, appModule):
		self.appModule = appModule

	def to_last_message(self):
		"""Move focus or caret to the last message in the active chat.

		Returns:
			bool: True if handled (caret moved, message focused, or announced empty),
				  False if no active chat message list is present.
		"""
		focusObj = api.getFocusObject()
		if self.appModule.ui_helper.is_message_object(focusObj):
			parent = getattr(focusObj, "parent", None)
			if parent and getattr(parent, "next", None):
				KeyboardInputGesture.fromName("end").send()
			else:
				message(getattr(focusObj, "name", ""))
			return True

		obj = self.appModule.ui_helper.getMessagesElement()
		if obj:
			last_child = getattr(obj, "lastChild", None)
			if last_child:
				try:
					last_child.setFocus()
					KeyboardInputGesture.fromName("end").send()
					return True
				except Exception:
					pass
			else:
				message(_("This chat is empty"))
				return True

		return False

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

	def _is_message_item(self, item):
		"""Determine if item is an actual message (and not a date header, separator, or container)."""
		if not item:
			return False
		try:
			if getattr(item, "role", None) != Role.LISTITEM:
				return False
			auto_id = getattr(item, "UIAAutomationId", "") or ""
			if auto_id == "Message_item":
				return True
			first = getattr(item, "firstChild", None)
			if first and getattr(first, "UIAAutomationId", "") == "Message_item":
				return True
			if getattr(item, "sender_message", None):
				return True
		except Exception:
			pass
		return False

	def _get_adjacent_item(self, item, forward=True):
		"""Find the nearest adjacent valid message item."""
		curr = item
		depth = 0
		while curr and depth < 6:
			curr = getattr(curr, "next" if forward else "previous", None)
			depth += 1
			if not curr:
				break
			if self._is_message_item(curr):
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

		log.debug("Attempting message focus restoration")
		for name, candidate in candidates:
			if not candidate:
				continue
			if self._safe_set_focus(candidate):
				log.debug(f"Successfully restored focus to {name} message candidate (role={getattr(candidate, 'role', None)})")
				return name

		log.warning("Message focus restoration failed: None of the three candidates (initial, next, previous) could be identified or focused")
		return False

	def start_delete_message(self, isCompleteDeletion=False):
		"""Begin the multi-step message deletion flow.

		Saves the initial object, next item, and previous item for focus restoration,
		then opens the context menu to find the delete option.
		"""
		obj = api.getFocusObject()
		if not self.appModule.ui_helper.is_message_object(obj):
			return False

		curr_item = obj
		if getattr(curr_item, "parent", None) and curr_item.parent.role == Role.LISTITEM:
			curr_item = curr_item.parent

		next_obj = self._get_adjacent_item(curr_item, forward=True)
		prev_obj = self._get_adjacent_item(curr_item, forward=False)

		self.appModule.isDelete = {
			"target": "messages",
			"isCompleteDeletion": isCompleteDeletion,
			"initial_obj": curr_item,
			"next_obj": next_obj,
			"prev_obj": prev_obj,
			"message": _("Message deleted on both sides") if isCompleteDeletion else _("Message deleted"),
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

				if not checkbox and (auto_id == "RevokeCheck" or role == Role.CHECKBOX):
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
		"""Execute the next step in the message deletion state machine.

		State 0: Find and click delete in context menu.
		State 1: Handle confirmation dialog (RevokeCheck checkbox + PrimaryButton).
		State "awaiting_confirmation": Track dialog interaction and restore focus on close.
		"""
		if not conf.get("confirmation_at_deletion"):
			speech.cancelSpeech()

		state = self.appModule.isDelete.get("state", 0) if isinstance(self.appModule.isDelete, dict) else 0
		auto_id = getattr(obj, "UIAAutomationId", "") or ""
		log.debug(f"Message deletion step: state={state}, role={getattr(obj, 'role', None)}, auto_id={auto_id}")

		if state == 0:
			if obj.role == Role.MENUITEM:
				for item in obj.parent.children:
					if item.firstChild and item.firstChild.name == icons_from_context_menu["delete"]:
						self.appModule.isDelete["state"] = 1
						log.debug("Message deletion: Clicked delete in context menu")
						item.doAction()
						return True
				log.warning("Message deletion: Delete option not found in context menu")
				self.appModule.isDelete = False
				CACHED_KEYS["escape"].send()
				return True
			else:
				self.appModule.isDelete = False
				return False

		elif state == 1 and (obj.role in (Role.CHECKBOX, Role.BUTTON, Role.DIALOG, Role.PANE) or auto_id in ("PrimaryButton", "SecondaryButton", "RevokeCheck", "CheckBox")):
			checkbox, primary_button, secondary_button = self._resolve_dialog_elements(obj)
			log.debug(f"Message deletion dialog resolved: checkbox={checkbox is not None}, primary_button={primary_button is not None}, secondary_button={secondary_button is not None}")

			# If a checkbox exists, adjust it according to isCompleteDeletion
			if checkbox:
				is_complete = self.appModule.isDelete.get("isCompleteDeletion", False)
				is_checked = State.CHECKED in getattr(checkbox, "states", set())
				log.debug(f"Message deletion checkbox: is_checked={is_checked}, target_is_complete={is_complete}")
				if is_complete and not is_checked:
					checkbox.doAction()
					log.debug("Message deletion: Toggled checkbox to checked")
				elif not is_complete and is_checked:
					checkbox.doAction()
					log.debug("Message deletion: Toggled checkbox to unchecked")

			if not primary_button:
				log.warning("PrimaryButton not found in message deletion dialog")
				self.appModule.isDelete = False
				return False

			# If confirmation setting is enabled, do not click. Focus on Delete and let user confirm.
			if conf.get("confirmation_at_deletion"):
				log.debug("Message deletion: confirmation_at_deletion is True, focusing PrimaryButton")
				self.appModule.isDelete["state"] = "awaiting_confirmation"
				try:
					primary_button.setFocus()
				except Exception as e:
					log.debug(f"Message deletion: Failed to set focus on PrimaryButton: {e}")
				return False

			# Automatic confirmation mode:
			log.debug("Message deletion: confirmation_at_deletion is False, invoking PrimaryButton")
			self.appModule.isDelete["confirmed_dismissal"] = "primary"
			self.appModule.isDelete["state"] = "awaiting_confirmation"
			primary_button.doAction()
			return True

		elif state == "awaiting_confirmation":
			dismiss_source = self.appModule.isDelete.get("confirmed_dismissal")
			if not dismiss_source:
				return False

			log.debug(f"Message deletion: dialog closed via {dismiss_source}, restoring focus")
			delete_msg = self.appModule.isDelete.get("message")
			focused_candidate = self.restore_deletion_focus()
			self.appModule.isDelete = False

			if dismiss_source == "primary" and focused_candidate != "initial":
				log.debug(f"Message was deleted (dismissal={dismiss_source}), announcing result")
				if delete_msg == "audio":
					playWaveFile(os.path.join(BASE_DIR, "delete.wav"))
				elif delete_msg:
					message(delete_msg)
			else:
				log.debug(f"Message deletion was cancelled via {dismiss_source}")

			if not focused_candidate:
				log.warning(f"Message deletion: none of the three candidates (initial, next, previous) could be identified or focused (dismissal={dismiss_source})")

			return False

		return False


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

	def script_toggle_live_chat(self, gesture):
		"""Toggle real-time background announcement of incoming messages."""
		if Chat_update.toggle(self.appModule):
			message(_("Automatic reading of messages is enabled"))
		else:
			message(_("Automatic reading of new messages is disabled"))

