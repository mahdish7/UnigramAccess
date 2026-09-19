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

	@script(description=_("Open UnigramAccess settings window"), gesture="kb:NVDA+ALT+U")
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
		import appModuleHandler
		appMod = appModuleHandler.getAppModuleFromProcessID(api.getFocusObject().processID)
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
		button = next(
			(
				c for c in getattr(toast, "children", [])
				if getattr(c, "UIAAutomationId", "") == "VerbButton" and getattr(c, "name", "") == "Audio"
			),
			None,
		)
		if button:
			try:
				button.doAction()
			except Exception:
				pass

	# End a call, decline call, or leave a voice chat
	@script(description=_("Press \"Decline call\" button  if there is an incoming call, \"End call\" button if a call is in progress or leave voice chat if it is active."), gesture="kb:ALT+N")
	def script_callCancellation(self, gesture):
		gesture.send()
		toast = self._getIncomingCallNotification()
		button = None
		if toast:
			button = next(
				(
					c for c in getattr(toast, "children", [])
					if getattr(c, "UIAAutomationId", "") == "VerbButton" and getattr(c, "name", "") == "Decline"
				),
				None,
			)
		if button:
			try:
				button.doAction()
			except Exception:
				pass
			return
		import appModuleHandler
		appMod = appModuleHandler.getAppModuleFromProcessID(api.getFocusObject().processID)
		if appMod and hasattr(appMod, 'script_callCancellation'):
			appMod.script_callCancellation(gesture)


class UnigramAccessSettings(SettingsPanel):
	title = _("UnigramAccess")
	listVoiceTypeAfterChatName = {
		"beforeName": _("Before chat name"),
		"afterName": _("After chat name"),
		"don'tVoice": _("Do not speak chat type")
	}
	listVoiceMessageRecordingIndicator = {
		"none": _("Revert to standard voice message recording behavior"),
		"text": _("Text notification"),
		"audio": _("sound notification")
	}
	listVoicingPerformanceIndicators = {
		"all": _("Announce all progress bars"),
		"none": _("Do not announce any progress bars"),
	}
	listSaySenderName = {
		"none": _("Do not say at all"),
		"sent": _("Only in sent messages"),
		"received": _("Only in received messages"),
		"all": _("In all messages")
	}
	list_actions_when_pressing_up_arrow_in_text_field = {
		"block": _("Do nothing"),
		"normal": _("Activate editing of last sent message"),
		"to_messages": _("Move focus to the last message in a chat"),
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
		# Selecting an interface language
		self.lang = settingsSizerHelper.addLabeledControl(_("Interface language in Unigram:"), wx.Choice, choices=list(listLanguages.values()))
		self.lang.SetStringSelection(listLanguages[conf.get("lang")])
		# Chat type announce mode
		self.voiceTypeAfterChatName = settingsSizerHelper.addLabeledControl(_("Speak the type of chat in the chat list:"), wx.Choice, choices=[self.listVoiceTypeAfterChatName[item] for item in self.listVoiceTypeAfterChatName])
		self.voiceTypeAfterChatName.SetStringSelection(self.listVoiceTypeAfterChatName[conf.get("voiceTypeAfterChatName")])
		# Message sender announcement
		self.saySenderName = settingsSizerHelper.addLabeledControl(_("Say the sender's name in:"), wx.Choice, choices=[self.listSaySenderName[item] for item in self.listSaySenderName])
		self.saySenderName.SetStringSelection(self.listSaySenderName[conf.get("saySenderName")])
		# Selecting the action when pressing the up arrow in the text editor
		self.action_when_pressing_up_arrow_in_text_field = settingsSizerHelper.addLabeledControl(
			_("Action when pressing the up arrow in the message edit field"), wx.Choice, choices=list(self.list_actions_when_pressing_up_arrow_in_text_field.values()))
		self.action_when_pressing_up_arrow_in_text_field.SetStringSelection(self.list_actions_when_pressing_up_arrow_in_text_field[conf.get("action_when_pressing_up_arrow_in_text_field")])
		# Report not seen before message content
		self.unreadBeforeMessageContent = settingsSizerHelper.addItem(wx.CheckBox(self, label=_("Speak \"Not Seen\" before reading contents of a message")))
		self.unreadBeforeMessageContent.SetValue(conf.get("unreadBeforeMessageContent"))
		# Announce the phrases "Administrator" and "Owner" on messages in communities
		self.notify_administrators_in_messages = settingsSizerHelper.addItem(wx.CheckBox(
			self, label=_('Announce the phrases "Administrator" and "Owner" on messages in communities')))
		self.notify_administrators_in_messages.SetValue(
			conf.get("notify administrators in messages"))
		# Speak active folder name when switching between them
		self.voiceFolderNames = settingsSizerHelper.addItem(wx.CheckBox(self, label=_("Speak folder names when switching between them")))
		self.voiceFolderNames.SetValue(conf.get("voiceFolderNames"))
		# Delete alert type
		self.audioPlaybackWhenDeleted = settingsSizerHelper.addItem(wx.CheckBox(self, label=_("Notify about deleting a message and chat with a sound")))
		self.audioPlaybackWhenDeleted.SetValue(conf.get("audioPlaybackWhenDeleted"))
		# Show confirmation window when deleting
		self.confirmation_at_deletion = settingsSizerHelper.addItem(wx.CheckBox(self, label=_("Display confirmation dialog when deleting messages and chats")))
		self.confirmation_at_deletion.SetValue(conf.get("confirmation_at_deletion"))
		# Type of notification when recording voice messages
		self.voiceMessageRecordingIndicator = settingsSizerHelper.addLabeledControl(_("Set voice message recording notification method as:"), wx.Choice, choices=[self.listVoiceMessageRecordingIndicator[item] for item in self.listVoiceMessageRecordingIndicator])
		self.voiceMessageRecordingIndicator.SetStringSelection(self.listVoiceMessageRecordingIndicator[conf.get("voiceMessageRecordingIndicator")])
		# Progress bar announce
		self.voicingPerformanceIndicators = settingsSizerHelper.addLabeledControl(_("Select the progress bar notification level:"), wx.Choice, choices=[self.listVoicingPerformanceIndicators[item] for item in self.listVoicingPerformanceIndicators])
		self.voicingPerformanceIndicators.SetStringSelection(self.listVoicingPerformanceIndicators[conf.get("voicingPerformanceIndicators")])
		# Processing messages containing links
		self.actionDescriptionForLinks = settingsSizerHelper.addItem(wx.CheckBox(self, label=_("Read description of URLs attached to messages")))
		self.actionDescriptionForLinks.SetValue(conf.get("actionDescriptionForLinks"))
		# Announcement of the full description of YouTube links
		self.voiceFullDescriptionOfLinkToYoutube = settingsSizerHelper.addItem(wx.CheckBox(self, label=_("Read full video description in YouTube URLs")))
		self.voiceFullDescriptionOfLinkToYoutube.SetValue(conf.get("voiceFullDescriptionOfLinkToYoutube"))
		# Announce file details on media buttons
		self.voiceMediaButtonDetails = settingsSizerHelper.addItem(wx.CheckBox(self, label=_("Announce file details (name, size, duration) on media buttons")))
		self.voiceMediaButtonDetails.SetValue(conf.get("voiceMediaButtonDetails"))
		# Report if the message contains a reaction
		self.voice_the_presence_of_a_reaction = settingsSizerHelper.addItem(wx.CheckBox(self, label=_("Announce if the message contains a reaction")))
		self.voice_the_presence_of_a_reaction.SetValue(conf.get("voice_the_presence_of_a_reaction"))
		# Fix toggle buttons for some users
		self.isFixedToggleButton = settingsSizerHelper.addItem(wx.CheckBox(self, label=_("Check this box if the voice message recording function or the voice message playback speed change function does not work properly")))
		self.isFixedToggleButton.SetValue(conf.get("isFixedToggleButton"))

		# Custom Log settings
		self.custom_log_level = settingsSizerHelper.addLabeledControl(_("Add-on log level:"), wx.Choice, choices=[self.listCustomLogLevels[item] for item in self.listCustomLogLevels])
		self.custom_log_level.SetStringSelection(self.listCustomLogLevels.get(conf.get("custom_log_level"), self.listCustomLogLevels["disabled"]))
		
		btnSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.btnOpenLog = wx.Button(self, label=_("Open Log File"))
		self.btnOpenLog.Bind(wx.EVT_BUTTON, self.onOpenLog)
		btnSizer.Add(self.btnOpenLog, 0, wx.ALL, 5)
		
		self.btnClearLog = wx.Button(self, label=_("Clear Log File"))
		self.btnClearLog.Bind(wx.EVT_BUTTON, self.onClearLog)
		btnSizer.Add(self.btnClearLog, 0, wx.ALL, 5)
		
		settingsSizerHelper.addItem(btnSizer)

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
		conf.set("notify administrators in messages",
		         self.notify_administrators_in_messages.IsChecked())
		conf.set("voiceFolderNames", self.voiceFolderNames.IsChecked())
		conf.set("confirmation_at_deletion", self.confirmation_at_deletion.IsChecked())
		conf.set("audioPlaybackWhenDeleted", self.audioPlaybackWhenDeleted.IsChecked())
		conf.set("voiceMessageRecordingIndicator", self.get_key(self.listVoiceMessageRecordingIndicator, self.voiceMessageRecordingIndicator.GetStringSelection()))
		conf.set("voicingPerformanceIndicators", self.get_key(self.listVoicingPerformanceIndicators, self.voicingPerformanceIndicators.GetStringSelection()))
		conf.set("lang", self.get_key(listLanguages, self.lang.GetStringSelection()))
		conf.set("action_when_pressing_up_arrow_in_text_field", self.get_key(self.list_actions_when_pressing_up_arrow_in_text_field, self.action_when_pressing_up_arrow_in_text_field.GetStringSelection()))
		conf.set("actionDescriptionForLinks", self.actionDescriptionForLinks.IsChecked())
		conf.set("voiceFullDescriptionOfLinkToYoutube", self.voiceFullDescriptionOfLinkToYoutube.IsChecked())
		conf.set("voiceMediaButtonDetails", self.voiceMediaButtonDetails.IsChecked())
		conf.set("voice_the_presence_of_a_reaction", self.voice_the_presence_of_a_reaction.IsChecked())
		conf.set("isFixedToggleButton", self.isFixedToggleButton.IsChecked())
		
		level = self.get_key(self.listCustomLogLevels, self.custom_log_level.GetStringSelection())
		conf.set("custom_log_level", level)
		from appModules.unigram_logger import ulog
		ulog.update_log_level()
