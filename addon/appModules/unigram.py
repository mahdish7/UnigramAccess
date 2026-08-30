# -*- coding:utf-8 -*-
from NVDAObjects.UIA import ListItem
from winBindings import user32 as winUser
import mouseHandler
from keyboardHandler import KeyboardInputGesture
import appModuleHandler
from ui import message
import api
from controlTypes import Role, State
import scriptHandler
from scriptHandler import script
import addonHandler
addonHandler.initTranslation()
import speech
from threading import Timer
from nvwave import playWaveFile
import os
from logHandler import log
import queueHandler
import re
from .data import *
from .text_window import *
from .cnf import conf, lang

# Import modularized components
from .overlays import (
	Audio_and_video_button,
	Message_list_item,
	SettingsPanelListItem,
	ExplanationCorrectAnswerInQuiz,
	EditableText,
)
from .trackers import (
	Saved_items,
	Title_change_tracking,
	Chat_update,
)
baseDir = os.path.join(os.path.dirname(__file__), "media")



from .unigram_ui import UnigramUIHelper
from .unigram_navigation import UnigramNavigation
from .unigram_calls import UnigramCalls
from .unigram_messages import UnigramMessages
from .unigram_media import UnigramMedia

class AppModule(appModuleHandler.AppModule):
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.saved_items = Saved_items()
		if conf.get("automatically announce new messages") and not Chat_update.active: Chat_update.restore(self)
		if conf.get("automatically announce activity in chats") and not Title_change_tracking.active: Title_change_tracking.restore(self.saved_items)
		self.app_version = self.productVersion
		# assign hotkeys for the function of reading messages by numbering
		for i in range(10): self.bindGesture("kb:NVDA+control+%d" % i, "reviewRecentMessage")
		self.ui_helper = UnigramUIHelper(self)
		self.nav_helper = UnigramNavigation(self)
		self.call_helper = UnigramCalls(self)
		self.msg_helper = UnigramMessages(self)
		self.media_helper = UnigramMedia(self)


	scriptCategory = "UnigramAccess"
	profile_panel_element = False
	isDelete = False
	isOpenProfile = False
	isSkipName = 0
	isRecord = False
	execute_context_menu_option = False
	is_exit_from_media = False
	keys = {
		"upArrow": KeyboardInputGesture.fromName("upArrow"),
		"downArrow": KeyboardInputGesture.fromName("downArrow"),
		"fixed_downArrow": KeyboardInputGesture.fromName("shift+downArrow"),
		"Applications": KeyboardInputGesture.fromName("Applications"),
		"escape": KeyboardInputGesture.fromName("escape"),
		"space": KeyboardInputGesture.fromName("space"),
	}


	def getMessagesElement(self):
		return self.ui_helper.getMessagesElement()

	def getChatsListElement(self):
		return self.ui_helper.getChatsListElement()

	def getElements(self):
		return self.ui_helper.getElements()
	
	def get_first_item(self):
		return self.ui_helper.get_first_item()


	def get_settings_panel(self):
		return self.ui_helper.get_settings_panel()

	def get_contacts_list(self):
		return self.ui_helper.get_contacts_list()

	def get_settings_list(self):
		return self.ui_helper.get_settings_list()


	def is_message_object(self, obj):
		return self.ui_helper.is_message_object(obj)





	# Go to chat list
	@script(description=_("Move focus to chat list"), gesture="kb:ALT+1")
	def script_toChatList(self, gesture, arg = False):
		return self.nav_helper.script_toChatList(gesture, arg)

	# Go to the last message in the chat
	@script(description=_("Move focus to the last message in an open chat"), gesture="kb:ALT+2")
	def script_toLastMessage(self, gesture):
		return self.nav_helper.script_toLastMessage(gesture)

	# Move focus to the list of chat folders 
	@script(description=_("Move focus to list of chat folders"), gesture="kb:ALT+4")
	def script_to_tabs_folder(self, gesture):
		return self.nav_helper.script_to_tabs_folder(gesture)


	def get_branch_list(self):
		return self.ui_helper.get_branch_list()

	@script(description=_("Move focus to the list of group threads"), gesture="kb:ALT+6")
	def script_move_focus_to_list_threads(self, gesture):
		return self.nav_helper.script_move_focus_to_list_threads(gesture)

	def get_profile_panel(self):
		return self.ui_helper.get_profile_panel()

	# Move focus to open profile
	@script(description=_("Move focus to open profile"), gesture="kb:ALT+5")
	def script_to_open_profile(self, gesture):
		return self.nav_helper.script_to_open_profile(gesture)

	# Announces the profile name and status in an open chat
	@script(description=_("Announce the name and status of an open chat"), gesture="kb:ALT+T")
	def script_read_profile_name(self, gesture):
		return self.nav_helper.script_read_profile_name(gesture)

	# Go to "unread messages" label
	@script(description=_("Move focus to 'unread messages' label"), gesture="kb:ALT+3")
	def script_goToTheLastUnreadMessage(self, gesture):
		return self.nav_helper.script_goToTheLastUnreadMessage(gesture)

	# Call if it's a contact, or enter a voice chat if it's a group
	@script(description=_("Call if it's a contact, or enter a voice chat if it's a group"), gesture="kb:shift+alt+C")
	def script_call(self, gesture):
		return self.call_helper.script_call(gesture)

	# Make a video call if it's a contact
	@script(description=_("Press the video call button"), gesture="kb:shift+alt+V")
	def script_videoCall(self, gesture):
		return self.call_helper.script_videoCall(gesture)

	# Function to open instant view
	@script(description=_("Press \"Instant view\" button, if it is included in the current message"), gesture="kb:ALT+Q")
	def script_instantView(self, gesture):
		return self.msg_helper.script_instantView(gesture)

	# End a call, decline call, or leave a voice chat
	def script_callCancellation(self, gesture):
		return self.call_helper.script_callCancellation(gesture)

	# Mute/unmute the microphone
	@script(description=_("Press \"Mute/unmute microphone\" button"), gesture="kb:ALT+A")
	def script_microphone(self, gesture):
		return self.call_helper.script_microphone(gesture)

	# Turn off/on the camera
	@script(description=_("Press \"Enable/disable camera\" button"), gesture="kb:ALT+V")
	def script_video(self, gesture):
		return self.call_helper.script_video(gesture)

	# Copy current message to clipboard
	@script(description=_("Copy the message if it contains text. If the focus is on a link, the link will be copied"), gesture="kb:control+C")
	def script_copyMessage(self, gesture):
		return self.msg_helper.script_copyMessage(gesture)

	# Copy message via context menu
	def script_copy(self, gesture):
		return self.msg_helper.script_copy(gesture)

	# Show message text in popup window
	def _script_show_text_message(self, gesture):
		return self.msg_helper._script_show_text_message(gesture)

	# Move the focus to the message input field. If the focus is already in this field, then move it to the last element that had focus before this field
	@script(description=_("Move the focus to the edit field. If the focus is already in the edit field, then after pressing the hotkey, it will move to where it was before"), gesture="kb:ALT+D")
	def script_moveFocusToTextMessage(self, gesture):
		return self.msg_helper.script_moveFocusToTextMessage(gesture)

	# Press the "Attach media" button
	@script(description=_("Press \"Attach file\" button"), gesture="kb:control+shift+A")
	def script_add_files(self, gesture):
		return self.msg_helper.script_add_files(gesture)

	# Press the "New Conversation" button
	@script(description=_("Press \"New conversation\" button"), gesture="kb:control+N")
	def script_new_conversation(self, gesture):
		return self.msg_helper.script_new_conversation(gesture)

	# Press the "More options" button in an open chat
	def script_showMoreOptions(self, gesture):
		return self.msg_helper.script_showMoreOptions(gesture)

	# Open navigation menu
	@script(description=_("Open navigation menu"), gesture="kb:ALT+M")
	def script_showMenu(self, gesture):
		return self.nav_helper.script_showMenu(gesture)

	# Function to open the profile of the current chat
	@script(description=_("Open current chat profile"), gesture="kb:alt+shift+P")
	def script_openProfile(self, gesture):
		return self.nav_helper.script_openProfile(gesture)


	# Processing the message that got into focus
	def action_message_focus(self, obj):
		keywords = obj.keywords
		sender = ""
		header = False
		admin_label = ""
		reactions = []
		sender_message = self.sender_message or ""
		item = obj.firstChild
		while item:
			if item.UIAAutomationId == "Question":
				# Processing messages containing a poll
				options, votes = "", ""
				for el in obj.children:
					if el.UIAAutomationId == "Votes": votes = ". "+el.name+". "
					elif el.role == Role.TOGGLEBUTTON and el.firstChild.role == Role.PROGRESSBAR:
						if el.childCount == 3: options += self.processing_of_answer_options_in_surveys(el)
						elif el.childCount == 2: options+=el.children[1].name+", "
				if options: options = _("Answer options")+": "+options
				obj.name = obj.name.replace(item.name+", ", item.name+votes+options)
			elif conf.get("actionDescriptionForLinks")  and item.role == Role.LINK and len(item.name) > 30 and not item.UIAAutomationId and item.firstChild.UIAAutomationId == "Label":
				# Processing the description of the link contained in the message
				description = item.name.strip()
				if not conf.get("voiceFullDescriptionOfLinkToYoutube") and description.startswith("YouTube "):
					description = description.split("\n")
					description = "\n".join(description[:2])
				# We escape all symbols \
				description = description.replace("\\", "").replace("http:\\", "\\\\")
				obj.name =re.sub(r"[.,]?{}|{}".format(keywords[3], keywords[2]), r". \n{}\g<0>".format(description), obj.name)
				obj.name =re.sub(r"(https?://\S+)\?[^\s,]+", r"\g<1>", obj.name)
			elif item.UIAAutomationId == "Subtitle" and len(item.name) < 15 and " / " in item.name:
				# Checking if a message is a voice message
				obj.name = item.name+", "+obj.name.replace(item.name[-5:], "")
			elif item.UIAAutomationId == "HeaderLabel": header = item
			item = item.next
		

		# Checking if a message is a call
		try:
			if obj.firstChild.role == Role.LINK and not obj.firstChild.name and obj.childCount == 7 and obj.children[1].UIAAutomationId == "TitleLabel" and obj.children[3].role == Role.STATICTEXT:
				a = obj.children[1].name
				b = ",".join(obj.children[3].name.split(",")[1:])
				obj.name = obj.name.replace(a, a+b)
				obj.index_last_part_in_message += len(b)
		except Exception: pass

		# Checking Whether to Add a Message Sender Name
		profile_name = self.saved_items.get("profile name")
		if conf.get("saySenderName") in ("sent", "all") and sender_message == "send" and not header: sender = _("You")+".\n"
		elif conf.get("saySenderName") in ("received", "all") and profile_name and obj.simpleFirstChild.UIAAutomationId not in ("Photo", "1HeaderLabel", "PhotoRoot") and obj.simpleFirstChild.location.left - obj.location.left < 35 and not header: sender = profile_name.firstChild.name+".\n"
		
		# Check the status of the message, whether it is read and sent
		# Checking only sent messages
		if keywords[0] in self.end_text:
			# If the message is read, delete information about it
			obj.name = obj.name.replace(keywords[0], ".", -1)
		elif keywords[1] in self.end_text:
			# If the message is not read, check whether it is necessary to display information about it
			if (sender_message == "received") or (profile_name and profile_name.childCount == 1):
				obj.name = obj.name.replace(keywords[1], ".", -1)
			elif conf.get("unreadBeforeMessageContent"):
				obj.name = obj.name.replace(keywords[1], ".", -1)
				obj.name = keywords[1][2:]+". "+obj.name
		if not conf.get("announce_end_of_message") and obj.index_last_part_in_message:
			obj.name = obj.name[:obj.index_last_part_in_message]
		if keywords[3] in self.end_text:
			# Removal of the phrase "administrator" and the phrase "owner" in messages
			list_text = obj.name.split("\n")
			key_phrases = phrase_administrator_in_message.get(conf.get("lang"), phrase_administrator_in_message["en"])
			en_key_phrases = phrase_administrator_in_message["en"]
			if not conf.get("notify administrators in messages") and len(list_text) > 1 and list_text[1] in (", "+key_phrases[0]+". \r", ", "+key_phrases[1]+". \r", ", "+en_key_phrases[0]+". \r", ", "+en_key_phrases[1]+". \r"):
				del list_text[1]
				obj.name = "\n".join(list_text)


		obj.name = sender+obj.name
		# Check if a message is selected
		if State.SELECTED in obj.states: obj.name = _("Selected")+". "+obj.name
		return obj.name

	# Processing the focused element from the list of chats
	def actionChatElementInFocus(self, obj):
		# If the user does not want to change the order of elements in the chat name, then we immediately terminate the function to improve the response speed
		if conf.get("voiceTypeAfterChatName") == "beforeName": return obj.name
		item = obj.firstChild
		while item:
			if item.UIAAutomationId == "TitleLabel":
				title = item.name
				type = obj.name.split(", ")[0] if not obj.name.startswith(title) else ""
				if not type: break
				elif type and conf.get("voiceTypeAfterChatName") == "afterName":
					obj.name = obj.name.replace(type+", "+title, title+", "+type, 1)
				elif type and conf.get("voiceTypeAfterChatName") == "don'tVoice":
					obj.name = obj.name.replace(type+", ", "", 1)
				break
			item = item.next
		return obj.name

	# Change the announce level of progress bars
	@script(description=_("Toggle progress bar announcements"), gesture="kb:ALT+U")
	def script_toggleVoicingPerformanceIndicators(self, gesture):
		if conf.get("voicingPerformanceIndicators") == "none":
			conf.set("voicingPerformanceIndicators", "all")
			message(_("Announce all progress bars"))
		else:
			conf.set("voicingPerformanceIndicators", "none")
			message(_("Do not announce any progress bars"))

	def script_reviewRecentMessage(self, gesture):
		return self.msg_helper.script_reviewRecentMessage(gesture)


	# Focus change tracking
	def event_gainFocus(self, obj, nextHandler):
		if conf.get("automatically announce new messages") and Chat_update.pause:
			# Since the timer is suspended when the program window is minimized, it needs to be restored as soon as the focus is set on some element in the window
			Chat_update.restore(self)
		if conf.get("automatically announce activity in chats") and Title_change_tracking.pause:
			# Since the timer is suspended when the program window is minimized, it needs to be restored as soon as the focus is set on some element in the window
			Title_change_tracking.restore(self.saved_items)
		if self.isSkipName:
			speech.cancelSpeech()
			self.isSkipName -= 1
			return True
		elif self.isOpenProfile:
			self.isOpenProfile = False
			panel = next((item for item in self.getElements() if item.UIAAutomationId == "ScrollingHost"), None)
			if panel:
				self.profile_panel_element = panel
				panel.firstChild.setFocus()
		elif self.execute_context_menu_option:
			try: targetButton = next((item for item in obj.parent.children if item.firstChild.name in self.execute_context_menu_option), False)
			except Exception: targetButton = False
			self.execute_context_menu_option = False
			if targetButton: targetButton.doAction()
			else: self.keys["escape"].send()
			return
		elif self.isRecord:
			self.isRecord.setFocus()
			self.isRecord = False
			self.isSkipName = 1
			return True
		elif self.isDelete:
			self.deleteMessageAndChat(obj)
			return
		if obj.role == Role.LISTITEM:
			speech.cancelSpeech()
			if self.is_message_object(obj):
				self.saved_items.save("last focus object", obj)
				obj.name = self.action_message_focus(obj)
			elif obj.parent.UIAAutomationId == "ChatsList":
				self.saved_items.save("last focused chat", obj)
				obj.name = self.actionChatElementInFocus(obj)
			elif obj.parent.UIAAutomationId == "ScrollingHost":
				if obj.name == "" and obj.childCount != 0:
					for item in obj.children: obj.name+=item.name
				elif obj.name.startswith("inlineQueryResult"):
					# Processing inline results
					name = [item.name for item in obj.children if item.name != ""]
					obj.name = ". ".join(name)
			elif obj.name == "Unigram.ViewModels.MessageViewModel": obj.name = obj.firstChild.name
			elif obj.name.startswith("EETypeRva"): obj.name = ", ".join([item.name for item in obj.children[1:]])
			elif obj.name == "Unigram.Entities.StoragePhoto": obj.name = _("Image")
			elif obj.name == "Unigram.ViewModels.Folders.FilterFlag": obj.name = obj.children[1].name
			elif obj.name.startswith("chatTheme {"): obj.name = obj.firstChild.name
			elif obj.name.startswith("forumTopic {\n  info = forumTopicInfo {"):
				labels = [label.name for label in obj.children if label.UIAAutomationId in ("TitleLabel", "BriefInfo", "TimeLabel") ]
				obj.name = ". ".join((labels[0], labels[2], labels[1]))
		elif obj.role == Role.EDITABLETEXT:
			try:
				# Determining if this input field is a message input field. If yes, then check if its title needs to be changed
				if obj.UIAAutomationId == "TextField" and ((obj.previous and obj.previous.UIAAutomationId == "ComposerHeaderCancel") or (obj.previous and obj.previous.previous and obj.previous.previous.UIAAutomationId == "ComposerHeaderCancel")):
					label = obj.previous.previous.previous if obj.previous and obj.previous.UIAAutomationId == "ButtonMore" else obj.previous.previous
					if label.name == "\uea4b": obj.name = _("Editing")
					elif label.name == "\uea4a": obj.name = _("Reply")
			except Exception: pass
		elif obj.role == Role.LINK:
			try:
				if obj.UIAAutomationId in ("Button", "Download") and obj.parent.parent.parent.UIAAutomationId == "Messages":
					# Announcing the name and size of the file when the focus is on the button to open or download this file
					def action(title, subtitle):
						arr = subtitle.split(" - ")
						for index, value in enumerate(arr):
							if ":" in value: arr[index] = _("Duration")+": "+arr[index]
							else: arr[index] = _("Size")+": "+arr[index]
						subtitle = ". ".join(arr)
						return ": "+title+". "+subtitle
					if obj.next.UIAAutomationId == "Title" and obj.next.next.UIAAutomationId == "Subtitle": obj.name += action(obj.next.name, obj.next.next.name)
					elif obj.next.next.UIAAutomationId == "Title" and obj.next.next.next.UIAAutomationId == "Subtitle": obj.name += action(obj.next.next.name, obj.next.next.next.name)
				elif obj.parent.UIAAutomationId in ("TextBlock", "Message"): speech.cancelSpeech()
			except Exception: pass
		elif obj.role == Role.BUTTON:
			try:
				# Add a label to unmute the microphone on a voice call
				# Add a label to turn on the camera on a voice call
				if obj.UIAAutomationId == "Audio" and obj.firstChild.name == "\ue720" and obj.next.UIAAutomationId == "AudioInfo": obj.name = obj.next.name
				elif obj.UIAAutomationId == "Video" and obj.firstChild.name == "\ue963": obj.name = _("Enable video")
				elif obj.UIAAutomationId == "Video" and obj.firstChild.name == "\ue964": obj.name = _("Disable video")
			except Exception: pass
		elif obj.role == Role.TOGGLEBUTTON:
			try:
				# Checking if a toggle button is an answer option in a vote
				if "reactionTypeEmoji {" in obj.name:
					obj.name = re.sub(r"^(.+)reactionTypeEmoji.+\"(.)\".+", r"\g<1>\g<2>", obj.name, flags=re.S)
				if obj.firstChild.UIAAutomationId == "Loading"  and obj.lastChild.UIAAutomationId == "Votes" and obj.childCount == 3: obj.name = self.processing_of_answer_options_in_surveys(obj)
			except Exception: pass
		if obj.name == "":
			if obj.firstChild and obj.firstChild.name in labels_in_buttons: # If the button contains an icon, check if the dictionary contains the label for that icon
				obj.name = labels_in_buttons[obj.firstChild.name]
			elif obj.UIAAutomationId in labels_for_buttons: # If the button has a label, separate it by words and assign it as the item name
				obj.name = labels_for_buttons[obj.UIAAutomationId]
			elif obj.UIAAutomationId:
				obj.name = ''.join(' ' + char.lower() if char.isupper() else char for char in obj.UIAAutomationId)
				obj.name = "".join(obj.name[1:]).capitalize()
			elif obj.childCount > 1:
				name = [item.name for item in obj.children if item.name != ""]
				obj.name = "/. ".join(name)
		nextHandler()

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		import comtypes
		try:
			if obj.role == Role.LISTITEM and  obj.name and obj.isFocusable:
				parent = obj.parent
				if parent.UIAAutomationId == "ChatFolders":
					self.tabs_folder_element = parent
					if conf.get("voiceFolderNames") and State.SELECTED in obj.states: self.change_chats_folder(obj, parent.UIAAutomationId)
					return True
				elif parent.UIAAutomationId == "Navigation":
					clsList.insert(0, SettingsPanelListItem)
					return True
				elif parent.UIAAutomationId in ("ChatsList", "TopicList"): return
				# We check whether the element contains phrases that will help us identify it as a message
				keywords = keywordsInMessages.get(conf.get("lang"), keywordsInMessages["en"])
				name = obj.name[-200:]
				self.sender_message = "received" if keywords[3] in name else "send" if keywords[2] in name else ""
				self.end_text = name
				if self.sender_message or (parent.role == Role.LISTITEM and parent.location.width > 800):
					clsList.insert(0, Message_list_item)
			elif conf.get("action_when_pressing_up_arrow_in_text_field") != "normal" and obj.role == Role.EDITABLETEXT and obj.UIAAutomationId == "TextField":
				# Add processing for pressing the up arrow key to the message input field
				clsList.insert(0, EditableText)
			elif obj.role == Role.BUTTON and obj.UIAAutomationId == "Profile":
				self.saved_items.save("profile name", obj)
			elif obj.UIAAutomationId in ("Audio", "Video"):
				clsList.insert(0, Audio_and_video_button)
			elif obj.role == Role.SLIDER and obj.UIAAutomationId == "Slider":
				self.saved_items.save("slider", obj)
			elif conf.get("voicingPerformanceIndicators") == "none" and obj.role == Role.PROGRESSBAR:
				clsList.pop(0)
		except (comtypes.COMError, AttributeError): pass

	def deleteMessageAndChat(self, obj):
		return self.msg_helper.deleteMessageAndChat(obj)

	@script(description=_("Delete a message or chat"), gestures=["kb:delete", "kb:ALT+delete"])
	def script_deletion(self, gesture):
		return self.msg_helper.script_deletion(gesture)
	@script(description=_("Delete message or chat from both sides"), gestures=["kb:shift+delete", "kb:ALT+shift+delete"])
	def script_completeDeletion(self, gesture):
		return self.msg_helper.script_completeDeletion(gesture)
	@script(description=_("Switch to selection mode"), gesture="kb:control+space")
	def script_selectMessage(self, gesture):
		return self.msg_helper.script_selectMessage(gesture)
	@script(description=_("Forward message"), gesture="kb:ALT+F")
	def script_forwardMessage(self, gesture):
		return self.msg_helper.script_forwardMessage(gesture)
	@script(description=_("Mark a chat as read"), gesture="kb:ALT+shift+R")
	def script_readMessage(self, gesture):
		return self.msg_helper.script_readMessage(gesture)
	@script(description=_("Save file as..."))
	def script_save_file(self, gesture):
		return self.msg_helper.script_save_file(gesture)
	@script(description=_("Pin a message or chat"))
	def script_attach(self, gesture):
		return self.msg_helper.script_attach(gesture)
	def activate_option_for_menu(self, option, list_name=False):
		return self.msg_helper.activate_option_for_menu(option, list_name)
	@script(gesture="kb:escape")
	def script_action_escape_key(self, gesture):
		gesture.send()
		if self.is_exit_from_media:
			lastFocusObject = self.saved_items.get("last focus object")
			if lastFocusObject and lastFocusObject.location:
				lastFocusObject.setFocus()
			self.is_exit_from_media = False

	__gestures = {
		"kb:escape": "action_escape_key",
		"kb:space": "actionMediaInMessage",
		"kb:control+D": "cancelVoiceMessageRecording",
		"kb:control+R": "recordingVoiceMessage",
		"kb:delete": "deletion",
		"kb:shift+delete": "completeDeletion",
	}

	def startDeleteMessage(self, isCompleteDeletion = False):
		return self.msg_helper.startDeleteMessage(isCompleteDeletion)


	def fixedDoAction(self, obj):
		import ctypes
		p = obj.location.center
		point = ctypes.wintypes.POINT()
		winUser.dll.GetCursorPos(ctypes.byref(point))
		winUser.dll.SetCursorPos(p.x, p.y)
		mouseHandler.executeMouseEvent(winUser.MOUSEEVENTF.LEFTDOWN, 0, 0)
		mouseHandler.executeMouseEvent(winUser.MOUSEEVENTF.LEFTUP, 0, 0)
		winUser.dll.SetCursorPos(point.x, point.y)

	def change_chats_folder(self, obj, parent):
		tab_items = obj.name.split(", ")
		count_chats = None
		last_selected_folder = self.saved_items.get("last selected folder")
		if last_selected_folder != tab_items[0]:
			self.saved_items.save("last selected folder", tab_items[0])
			if len(tab_items) > 1 and tab_items[1] != "0": count_chats = tab_items[1]
		else: return False
		text = self.saved_items.get("last selected folder")
		if count_chats: text+= ", "+count_chats
		queueHandler.queueFunction(queueHandler.eventQueue, message, text)

	# Data copy function for broadcasting
	@script(description=_("Copy data for broadcasting to the clipboard"), gesture="kb:ALT+shift+L")
	def script_copy_data_for_broadcast(self, gesture):
		return self.msg_helper.script_copy_data_for_broadcast(gesture)



	
	


	def script_set_reaction(self, gesture):
		return self.msg_helper.script_set_reaction(gesture)


	def processing_of_answer_options_in_surveys(self, obj):
		tmp_el = obj.firstChild
		processing_of_answer_options_in_surveys = False # Checking the correctness of the answer in the vote
		while tmp_el.next: # Going through the elements, checking if this option is the correct answer in the vote
			tmp_el = tmp_el.next
			if tmp_el.name == "\uf13e": processing_of_answer_options_in_surveys = True
		_("Right answer") # This is necessary for this phrase to appear in the translation dictionary
		return f'{_("Right answer")+": " if processing_of_answer_options_in_surveys else ""}{obj.name}, '





	@script(description=_("Enable automatic reading of new messages in the current chat"), gesture="kb:ALT+L")
	def script_toggle_live_chat(self, gesture):
		if Chat_update.toggle(self): message(_("Automatic reading of messages is enabled"))
		else: message(_("Automatic reading of new messages is disabled"))
	
	@script(description=_("Show a list of all UnigramAccess shortcuts"), gesture="kb:ALT+H")
	def script_help(self, gesture):
		a = addonHandler.getCodeAddon() or next((item for item in list(addonHandler.getAvailableAddons()) if item.name in ("UnigramAccess", "unigramAccess")), None)
		a = a.getDocFilePath()
		# We replace the file extension, because we need an md file
		a = a[:-4]+"md"
		with open(a, "r", encoding="utf-8") as file:
			text = file.read()
		blocks = text.split("\n\n")
		count_rows = [len(item.split("\n")) for item in blocks]
		index = count_rows.index(max(count_rows))
		text = blocks[index]
		text = text.replace("* ", "")
		text = text.replace("## ", "")
		TextWindow(text.strip(), _("List of shortcuts"), readOnly=True)


	@script(description=_("Go to the end"), gesture="kb:ALT+end")
	def script_to_down(self, gesture):
		return self.nav_helper.script_to_down(gesture)

	@script(description=_("Go to the list with search results"), gesture="kb:ALT+I")
	def script_go_to_list_search_results(self, gesture):
		return self.nav_helper.script_go_to_list_search_results(gesture)
	
	@script(description=_("Go to the next search result"), gesture="kb:F3")
	def script_go_to_previous_search_result(self, gesture):
		return self.nav_helper.script_go_to_previous_search_result(gesture)
	
	@script(description=_("Go to the previous search result"), gesture="kb:shift+F3")
	def script_go_to_next_search_result(self, gesture):
		return self.nav_helper.script_go_to_next_search_result(gesture)


	# The function of changing the playback speed of a voice message
	@script(description=_("Increase/decrease the playback speed of voice messages"), gesture="kb:ALT+S")
	def script_voiceMessageAcceleration(self, gesture):
		return self.media_helper.script_voiceMessageAcceleration(gesture)

	# Audio player close function
	@script(description=_("Close audio player"), gesture="kb:ALT+E")
	def script_closingVoiceMessage(self, gesture, isMessage = True):
		return self.media_helper.script_closingVoiceMessage(gesture, isMessage)

	# Voice message pause function
	@script(description=_("Play/pause the voice message currently playing"), gesture="kb:ALT+P")
	def script_pauseVoiceMessage(self, gesture):
		return self.media_helper.script_pauseVoiceMessage(gesture)

	# Playing and opening media with the space bar
	@script(description=_("Play or stop focused media"), gesture="kb:space")
	def script_actionMediaInMessage(self, gesture):
		return self.media_helper.script_actionMediaInMessage(gesture)

	# Voice message recording function
	@script(description=_("Start or stop recording a voice message"), gesture="kb:control+R")
	def script_recordingVoiceMessage(self, gesture):
		return self.media_helper.script_recordingVoiceMessage(gesture)

	# Voice message discard function
	@script(description=_("Cancel voice message recording or cycle notification mode"), gesture="kb:control+D")
	def script_cancelVoiceMessageRecording(self, gesture):
		return self.media_helper.script_cancelVoiceMessageRecording(gesture)

	def rewind_voice_message(self, direction):
		return self.media_helper.rewind_voice_message(direction)

	def script_rewind_voice_message(self, gesture):
		return self.media_helper.script_rewind_voice_message(gesture)

	@script(description=_("Fast forward a voice message"), gesture="kb:control+ALT+rightArrow")	
	def script_rewindVoiceMessageForward(self, gesture):
		return self.media_helper.script_rewindVoiceMessageForward(gesture)

	@script(description=_("Rewind voice message"), gesture="kb:control+ALT+leftArrow")
	def script_rewindVoiceMessageBack(self, gesture):
		return self.media_helper.script_rewindVoiceMessageBack(gesture)

	# A timer that checks if the voice message has been converted to text
	def waiting_for_recognition(self, obj):
		return self.media_helper.waiting_for_recognition(obj)

	# Converting voice messages to text
	@script(description=_("Convert voice message to text"), gesture="kb:NVDA+ALT+R")
	def script_Recognize_voice_message(self, gesture):
		return self.media_helper.script_Recognize_voice_message(gesture)
