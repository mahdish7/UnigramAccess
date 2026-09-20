# -*- coding: utf-8 -*-
import globalPluginHandler
import globalVars
import addonHandler
from scriptHandler import script
import api
import ui
import gui
from gui.settingsDialogs import SettingsPanel
import wx
addonHandler.initTranslation()
from appModules.cnf import conf, listLanguages


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = "UnigramAccess"
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(UnigramAccessSettings)

	def terminate(self):
		super().terminate()
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(UnigramAccessSettings)

	@script(description=_("Open UnigramAccess settings panel"), gesture="kb:NVDA+ALT+U")
	def script_open_settings_dialog(self, gesture, arg = False):
		wx.CallAfter(gui.mainFrame.popupSettingsDialog, gui.settingsDialogs.NVDASettingsDialog, UnigramAccessSettings)

	@staticmethod
	def _getIncomingCallNotification():
		"""Locate the incoming call toast notification window on the desktop."""
		desktop = api.getDesktopObject()
		for item in getattr(desktop, "children", []):
			first_child = getattr(item, "firstChild", None)
			if first_child and getattr(first_child, "UIAAutomationId", "") == "ToastCenterScrollViewer":
				for toast in getattr(first_child, "children", []):
					if getattr(toast, "UIAAutomationId", "") == "PriorityToastView":
						return toast
		return None

	@staticmethod
	def _getCallerName(toast):
		"""Extract the caller's name from the incoming call toast notification."""
		title_obj = next(
			(c for c in getattr(toast, "children", []) if getattr(c, "UIAAutomationId", "") == "Title"),
			None,
		)
		if title_obj:
			return getattr(title_obj, "name", "") or ""
		return ""

	# Read caller name on incoming call
	@script(description=_("Read incoming caller name"), gesture="kb:ALT+T")
	def script_readIncomingCallerName(self, gesture):
		toast = self._getIncomingCallNotification()
		if toast:
			caller = self._getCallerName(toast)
			if caller:
				ui.message(caller)
				return
		focus = api.getFocusObject()
		if focus:
			import appModuleHandler
			appMod = appModuleHandler.getAppModuleFromProcessID(focus.processID)
			if appMod and hasattr(appMod, "script_read_profile_name"):
				appMod.script_read_profile_name(gesture)
				return
		gesture.send()

	# Call answer
	@script(description=_("Accept call"), gesture="kb:ALT+Y")
	def script_answeringCall(self, gesture):
		gesture.send()
		toast = self._getIncomingCallNotification()
		if not toast:
			return
		verb_buttons = [
			c for c in getattr(toast, "children", [])
			if getattr(c, "UIAAutomationId", "") == "VerbButton"
		]
		button = next((c for c in verb_buttons if getattr(c, "name", "") == "Audio"), None)
		if not button and verb_buttons:
			button = verb_buttons[0]
		if button:
			try:
				button.doAction()
			except Exception:
				pass

	# End a call, decline call, or leave a voice chat
	@script(description=_("Decline incoming call, end active call, or leave voice chat"), gesture="kb:ALT+N")
	def script_callCancellation(self, gesture):
		gesture.send()
		toast = self._getIncomingCallNotification()
		button = None
		if toast:
			verb_buttons = [
				c for c in getattr(toast, "children", [])
				if getattr(c, "UIAAutomationId", "") == "VerbButton"
			]
			button = next((c for c in verb_buttons if getattr(c, "name", "") == "Decline"), None)
			if not button and verb_buttons:
				button = verb_buttons[1] if len(verb_buttons) > 1 else verb_buttons[0]
		if button:
			try:
				button.doAction()
			except Exception:
				pass
			return
		focus = api.getFocusObject()
		if focus:
			import appModuleHandler
			appMod = appModuleHandler.getAppModuleFromProcessID(focus.processID)
			if appMod and hasattr(appMod, 'script_callCancellation'):
				appMod.script_callCancellation(gesture)


class UnigramAccessSettings(SettingsPanel):
	title = _("UnigramAccess")
	listVoiceTypeAfterChatName = {
		"beforeName": _("Before chat name"),
		"afterName": _("After chat name"),
		"don'tVoice": _("Do not announce")
	}
	listVoiceMessageRecordingIndicator = {
		"none": _("Standard Telegram behavior"),
		"text": _("Text notification"),
		"audio": _("Sound notification")
	}
	listSaySenderName = {
		"none": _("Do not announce"),
		"send": _("Sent messages only"),
		"received": _("Received messages only"),
		"all": _("All messages")
	}
	list_actions_when_pressing_up_arrow_in_text_field = {
		"edit": _("Edit last sent message"),
		"to_messages": _("Move focus to last message"),
		"do_nothing": _("Do nothing"),
	}
	
	listCustomLogLevels = {
		"disabled": _("Disabled"),
		"error": _("Error"),
		"warning": _("Warning"),
		"info": _("Info"),
		"debug": _("Debug"),
	}
	
	def makeSettings(self, settingsSizer):
		settingsSizerHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		# ── 1. General and Navigation ────────────────────────────────────
		genBox = wx.StaticBox(self, label=_("General and Navigation"))
		genSizer = wx.StaticBoxSizer(genBox, wx.VERTICAL)
		genHelper = gui.guiHelper.BoxSizerHelper(genBox, sizer=genSizer)

		self.lang = genHelper.addLabeledControl(
			_("Interface language in Unigram:"),
			wx.Choice,
			choices=list(listLanguages.values())
		)
		self.lang.SetStringSelection(listLanguages[conf.get("lang")])

		self.voiceTypeAfterChatName = genHelper.addLabeledControl(
			_("Chat type announcement in chats list:"),
			wx.Choice,
			choices=[self.listVoiceTypeAfterChatName[item] for item in self.listVoiceTypeAfterChatName]
		)
		self.voiceTypeAfterChatName.SetStringSelection(self.listVoiceTypeAfterChatName[conf.get("voiceTypeAfterChatName")])

		settingsSizerHelper.addItem(genSizer)

		# ── 2. Messages and Reading ──────────────────────────────────────
		msgBox = wx.StaticBox(self, label=_("Messages and Reading"))
		msgSizer = wx.StaticBoxSizer(msgBox, wx.VERTICAL)
		msgHelper = gui.guiHelper.BoxSizerHelper(msgBox, sizer=msgSizer)

		self.saySenderName = msgHelper.addLabeledControl(
			_("Announce sender name:"),
			wx.Choice,
			choices=[self.listSaySenderName[item] for item in self.listSaySenderName]
		)
		self.saySenderName.SetStringSelection(self.listSaySenderName[conf.get("saySenderName")])

		self.action_when_pressing_up_arrow_in_text_field = msgHelper.addLabeledControl(
			_("Up arrow action in empty message edit field:"),
			wx.Choice,
			choices=list(self.list_actions_when_pressing_up_arrow_in_text_field.values())
		)
		self.action_when_pressing_up_arrow_in_text_field.SetStringSelection(
			self.list_actions_when_pressing_up_arrow_in_text_field[conf.get("action_when_pressing_up_arrow_in_text_field")]
		)

		self.unreadBeforeMessageContent = msgHelper.addItem(
			wx.CheckBox(msgBox, label=_("Speak \"Not seen\" before message text"))
		)
		self.unreadBeforeMessageContent.SetValue(conf.get("unreadBeforeMessageContent"))

		self.announce_end_of_message = msgHelper.addItem(
			wx.CheckBox(msgBox, label=_("Announce timestamp and reactions at end of messages"))
		)
		self.announce_end_of_message.SetValue(conf.get("announce_end_of_message"))

		self.notify_administrators_in_messages = msgHelper.addItem(
			wx.CheckBox(msgBox, label=_('Announce "Administrator" and "Owner" badges in communities'))
		)
		self.notify_administrators_in_messages.SetValue(conf.get("notify administrators in messages"))

		self.actionDescriptionForLinks = msgHelper.addItem(
			wx.CheckBox(msgBox, label=_("Read descriptions of message links"))
		)
		self.actionDescriptionForLinks.SetValue(conf.get("actionDescriptionForLinks"))

		self.cleanLinkDescriptions = msgHelper.addItem(
			wx.CheckBox(msgBox, label=_("Clean up repetitive and boilerplate text in link previews"))
		)
		self.cleanLinkDescriptions.SetValue(conf.get("cleanLinkDescriptions"))

		settingsSizerHelper.addItem(msgSizer)

		# ── 3. Live Monitoring and Activity ──────────────────────────────
		liveBox = wx.StaticBox(self, label=_("Live Monitoring and Activity"))
		liveSizer = wx.StaticBoxSizer(liveBox, wx.VERTICAL)
		liveHelper = gui.guiHelper.BoxSizerHelper(liveBox, sizer=liveSizer)

		self.automatically_announce_new_messages = liveHelper.addItem(
			wx.CheckBox(liveBox, label=_("Automatically read incoming messages in active chat"))
		)
		self.automatically_announce_new_messages.SetValue(conf.get("automatically announce new messages"))

		self.automatically_announce_activity_in_chats = liveHelper.addItem(
			wx.CheckBox(liveBox, label=_("Announce chat activity (typing, online status)"))
		)
		self.automatically_announce_activity_in_chats.SetValue(conf.get("automatically announce activity in chats"))

		settingsSizerHelper.addItem(liveSizer)

		# ── 4. Media and Voice Messages ──────────────────────────────────
		mediaBox = wx.StaticBox(self, label=_("Media and Voice Messages"))
		mediaSizer = wx.StaticBoxSizer(mediaBox, wx.VERTICAL)
		mediaHelper = gui.guiHelper.BoxSizerHelper(mediaBox, sizer=mediaSizer)

		self.voiceMessageRecordingIndicator = mediaHelper.addLabeledControl(
			_("Voice recording notification mode:"),
			wx.Choice,
			choices=[self.listVoiceMessageRecordingIndicator[item] for item in self.listVoiceMessageRecordingIndicator]
		)
		self.voiceMessageRecordingIndicator.SetStringSelection(
			self.listVoiceMessageRecordingIndicator[conf.get("voiceMessageRecordingIndicator")]
		)

		self.voiceMediaButtonDetails = mediaHelper.addItem(
			wx.CheckBox(mediaBox, label=_("Announce file details (name, size, duration) on media buttons"))
		)
		self.voiceMediaButtonDetails.SetValue(conf.get("voiceMediaButtonDetails"))

		self.voiceDownloadProgress = mediaHelper.addItem(
			wx.CheckBox(mediaBox, label=_("Announce file download progress"))
		)
		self.voiceDownloadProgress.SetValue(conf.get("voiceDownloadProgress"))

		settingsSizerHelper.addItem(mediaSizer)

		# ── 5. Deletion and Confirmation ─────────────────────────────────
		delBox = wx.StaticBox(self, label=_("Deletion and Confirmation"))
		delSizer = wx.StaticBoxSizer(delBox, wx.VERTICAL)
		delHelper = gui.guiHelper.BoxSizerHelper(delBox, sizer=delSizer)

		self.confirmation_at_deletion = delHelper.addItem(
			wx.CheckBox(delBox, label=_("Show confirmation dialog when deleting messages and chats"))
		)
		self.confirmation_at_deletion.SetValue(conf.get("confirmation_at_deletion"))

		self.audioPlaybackWhenDeleted = delHelper.addItem(
			wx.CheckBox(delBox, label=_("Play sound when deleting messages and chats"))
		)
		self.audioPlaybackWhenDeleted.SetValue(conf.get("audioPlaybackWhenDeleted"))

		settingsSizerHelper.addItem(delSizer)

		# ── 6. Logging and Diagnostics ───────────────────────────────────
		logBox = wx.StaticBox(self, label=_("Logging and Diagnostics"))
		logSizer = wx.StaticBoxSizer(logBox, wx.VERTICAL)
		logHelper = gui.guiHelper.BoxSizerHelper(logBox, sizer=logSizer)

		self.custom_log_level = logHelper.addLabeledControl(
			_("Add-on log level:"),
			wx.Choice,
			choices=[self.listCustomLogLevels[item] for item in self.listCustomLogLevels]
		)
		self.custom_log_level.SetStringSelection(
			self.listCustomLogLevels.get(conf.get("custom_log_level"), self.listCustomLogLevels["disabled"])
		)

		btnSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.btnOpenLog = wx.Button(logBox, label=_("Open Log File"))
		self.btnOpenLog.Bind(wx.EVT_BUTTON, self.onOpenLog)
		btnSizer.Add(self.btnOpenLog, 0, wx.ALL, 5)

		self.btnClearLog = wx.Button(logBox, label=_("Clear Log File"))
		self.btnClearLog.Bind(wx.EVT_BUTTON, self.onClearLog)
		btnSizer.Add(self.btnClearLog, 0, wx.ALL, 5)

		logHelper.addItem(btnSizer)

		settingsSizerHelper.addItem(logSizer)

	def onOpenLog(self, evt):
		from appModules.unigram_logger import ulog
		ulog.open_log_file()
		
	def onClearLog(self, evt):
		from appModules.unigram_logger import ulog
		ulog.clear_log_file()
		gui.messageBox(_("Log file has been cleared successfully."), _("Success"), wx.OK | wx.ICON_INFORMATION)

	def get_key(self, d, value):
		for k, v in d.items():
			if v == value: return k

	def onSave(self):
		conf.set("voiceTypeAfterChatName", self.get_key(self.listVoiceTypeAfterChatName, self.voiceTypeAfterChatName.GetStringSelection()))
		conf.set("saySenderName", self.get_key(self.listSaySenderName, self.saySenderName.GetStringSelection()))
		conf.set("unreadBeforeMessageContent", self.unreadBeforeMessageContent.IsChecked())
		conf.set("announce_end_of_message", self.announce_end_of_message.IsChecked())
		conf.set("automatically announce new messages", self.automatically_announce_new_messages.IsChecked())
		conf.set("automatically announce activity in chats", self.automatically_announce_activity_in_chats.IsChecked())
		conf.set("notify administrators in messages",
		         self.notify_administrators_in_messages.IsChecked())
		conf.set("confirmation_at_deletion", self.confirmation_at_deletion.IsChecked())
		conf.set("audioPlaybackWhenDeleted", self.audioPlaybackWhenDeleted.IsChecked())
		conf.set("voiceMessageRecordingIndicator", self.get_key(self.listVoiceMessageRecordingIndicator, self.voiceMessageRecordingIndicator.GetStringSelection()))
		conf.set("voiceDownloadProgress", self.voiceDownloadProgress.IsChecked())
		conf.set("lang", self.get_key(listLanguages, self.lang.GetStringSelection()))
		conf.set("action_when_pressing_up_arrow_in_text_field", self.get_key(self.list_actions_when_pressing_up_arrow_in_text_field, self.action_when_pressing_up_arrow_in_text_field.GetStringSelection()))
		conf.set("actionDescriptionForLinks", self.actionDescriptionForLinks.IsChecked())
		conf.set("cleanLinkDescriptions", self.cleanLinkDescriptions.IsChecked())
		conf.set("voiceMediaButtonDetails", self.voiceMediaButtonDetails.IsChecked())
		
		level = self.get_key(self.listCustomLogLevels, self.custom_log_level.GetStringSelection())
		conf.set("custom_log_level", level)
		from appModules.unigram_logger import ulog
		ulog.update_log_level()
