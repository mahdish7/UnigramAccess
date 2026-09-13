# -*- coding:utf-8 -*-
# UnigramAccess: Voice and video call controls.

import api
from controlTypes import Role
import queueHandler
from threading import Timer
from ui import message

import addonHandler

addonHandler.initTranslation()

from .unigram_utils import clickElementWithMouse


class UnigramCalls:
	"""Handles call-related actions in Unigram.

	Provides voice/video call initiation, microphone/camera toggling,
	and call cancellation/decline functionality.
	"""

	def __init__(self, appModule):
		self.appModule = appModule

	def script_call(self, gesture):
		"""Initiate a voice call or join a voice chat."""
		try:
			targetButton = next(
				(
					item
					for item in self.appModule.ui_helper.getElements()
					if (item.role == Role.BUTTON and item.UIAAutomationId == "Call")
					or (item.role == Role.LINK and item.UIAAutomationId == "GroupCall")
					or (
						item.next
						and item.next.UIAAutomationId == "Audio"
						and item.firstChild
						and item.firstChild.UIAAutomationId == "TitleInfo"
					)
				),
				False,
			)
		except Exception:
			targetButton = False
		if targetButton:
			targetButton.doAction()
		else:
			message(_("Call unavailable"))

	def script_videoCall(self, gesture):
		"""Initiate a video call."""
		targetButton = next(
			(item for item in self.appModule.ui_helper.getElements() if item.role == Role.BUTTON and item.UIAAutomationId == "VideoCall"),
			False,
		)
		if targetButton:
			targetButton.doAction()
		else:
			message(_("Video call not available"))

	def script_callCancellation(self, gesture):
		"""Hang up, decline an incoming call, or leave a voice chat."""
		elements = self.appModule.ui_helper.getElements()
		targetButton = next(
			(
				item
				for item in elements
				if getattr(item, "role", None) in (Role.BUTTON, Role.LINK)
				and (
					getattr(item, "UIAAutomationId", "") in ("Leave", "Dismiss")
					or (getattr(item, "UIAAutomationId", "") == "Accept" and item.previous and getattr(item.previous, "UIAAutomationId", "") == "Audio")
				)
			),
			False,
		)
		if targetButton:
			lastFocus = api.getFocusObject()
			btn_name = getattr(targetButton, "name", "") or _("Leave")
			message(btn_name)
			clickElementWithMouse(targetButton)
			if lastFocus:
				try:
					lastFocus.setFocus()
				except Exception:
					pass
			return True
		return False

	@staticmethod
	def _getMicrophoneState(button):
		"""Determine whether microphone is on or off based strictly on icon glyphs."""
		first_child = getattr(button, "firstChild", None)
		child_name = getattr(first_child, "name", "") if first_child else ""
		if child_name == "\ue720":
			return _("Microphone turned on")
		elif child_name in ("\ue74f", "\uf781"):
			return _("Microphone turned off")
		return None

	@staticmethod
	def _getVideoState(button):
		"""Determine whether camera is on or off based strictly on icon glyphs."""
		first_child = getattr(button, "firstChild", None)
		child_name = getattr(first_child, "name", "") if first_child else ""
		if child_name == "\ue964":
			return _("Camera turned on")
		elif child_name == "\ue963":
			return _("Camera turned off")
		return None

	def script_microphone(self, gesture):
		"""Toggle microphone mute/unmute state."""
		obj = api.getFocusObject()
		targetButton = next(
			(
				item
				for item in self.appModule.ui_helper.getElements()
				if getattr(item, "UIAAutomationId", "") == "Audio"
				and getattr(item, "role", None) in (Role.BUTTON, Role.TOGGLEBUTTON)
			),
			None,
		)

		if targetButton:
			try:
				clickElementWithMouse(targetButton)
			except Exception:
				try:
					targetButton.doAction()
				except Exception:
					pass

			if obj:
				try:
					obj.setFocus()
				except Exception:
					pass

			def speakAudioState():
				btn = next(
					(
						item
						for item in self.appModule.ui_helper.getElements()
						if getattr(item, "UIAAutomationId", "") == "Audio"
						and getattr(item, "role", None) in (Role.BUTTON, Role.TOGGLEBUTTON)
					),
					targetButton,
				)
				state_text = self._getMicrophoneState(btn)
				if state_text:
					queueHandler.queueFunction(queueHandler.eventQueue, message, state_text)

			Timer(0.2, speakAudioState).start()
			return True
		return False

	def script_video(self, gesture):
		"""Toggle camera on/off."""
		obj = api.getFocusObject()
		targetButton = next(
			(
				item
				for item in self.appModule.ui_helper.getElements()
				if getattr(item, "UIAAutomationId", "") == "Video"
				and getattr(item, "role", None) in (Role.BUTTON, Role.TOGGLEBUTTON)
			),
			None,
		)

		if targetButton:
			try:
				clickElementWithMouse(targetButton)
			except Exception:
				try:
					targetButton.doAction()
				except Exception:
					pass

			if obj:
				try:
					obj.setFocus()
				except Exception:
					pass

			def speakVideoState():
				btn = next(
					(
						item
						for item in self.appModule.ui_helper.getElements()
						if getattr(item, "UIAAutomationId", "") == "Video"
						and getattr(item, "role", None) in (Role.BUTTON, Role.TOGGLEBUTTON)
					),
					targetButton,
				)
				state_text = self._getVideoState(btn)
				if state_text:
					queueHandler.queueFunction(queueHandler.eventQueue, message, state_text)

			Timer(0.2, speakVideoState).start()
			return True
		return False

