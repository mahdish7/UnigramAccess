# -*- coding:utf-8 -*-
# UnigramAccess: Voice and video call controls.

import api
from controlTypes import Role
import queueHandler
from threading import Timer
from ui import message

import addonHandler

addonHandler.initTranslation()

from .unigram_utils import fixedDoAction


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
		targetButton = next(
			(
				item
				for item in self.appModule.ui_helper.getElements()[1:]
				if (item.UIAAutomationId == "Accept" and item.previous and item.previous.UIAAutomationId == "Audio")
				or (item.UIAAutomationId == "Leave" and item.firstChild and item.firstChild.name == "\ue711")
				or (item.previous and item.previous.UIAAutomationId == "Audio" and item.firstChild and item.firstChild.name == "\ue711")
			),
			False,
		)
		if targetButton:
			lastFocus = api.getFocusObject()
			message(targetButton.name)
			fixedDoAction(targetButton)
			lastFocus.setFocus()

	def script_microphone(self, gesture):
		"""Toggle microphone mute/unmute state."""
		obj = api.getFocusObject()
		targetButton = False
		isVoiceChat = False
		for item in self.appModule.ui_helper.getElements():
			if (
				item.UIAAutomationId == "Audio"
				and item.previous
				and item.previous.UIAAutomationId == "Video"
				and item.next
				and item.next.UIAAutomationId == "Accept"
			):
				targetButton = item
				break
			elif item.UIAAutomationId == "Audio" and item.next.UIAAutomationId == "AudioInfo":
				targetButton = item
				isVoiceChat = True
				break
		if targetButton:
			if isVoiceChat:
				targetButton.doAction()
				obj.setFocus()

				def speakState():
					queueHandler.queueFunction(queueHandler.eventQueue, message, targetButton.next.name)

				Timer(0.1, speakState).start()
				return True
			fixedDoAction(targetButton)
			obj.setFocus()

			def speakState():
				queueHandler.queueFunction(queueHandler.eventQueue, message, targetButton.name)

			Timer(0.1, speakState).start()

	def script_video(self, gesture):
		"""Toggle camera on/off."""
		obj = api.getFocusObject()
		targetButton = False
		isVoiceChat = False
		for item in self.appModule.ui_helper.getElements():
			if (
				item.UIAAutomationId == "Video"
				and item.next.UIAAutomationId == "Audio"
				and item.next.next.UIAAutomationId == "Accept"
			):
				targetButton = item
				break
			elif item.UIAAutomationId == "Video" and item.next.UIAAutomationId == "VideoInfo":
				targetButton = item
				isVoiceChat = True
				break
		if targetButton:
			if isVoiceChat:
				targetButton.doAction()
				obj.setFocus()

				def speakState():
					if targetButton.firstChild.name == "\ue964":
						queueHandler.queueFunction(queueHandler.eventQueue, message, _("Camera on"))
					elif targetButton.firstChild.name == "\ue963":
						queueHandler.queueFunction(queueHandler.eventQueue, message, _("Camera off"))

				Timer(0.1, speakState).start()
				return
			fixedDoAction(targetButton)
			obj.setFocus()

			def speakState():
				queueHandler.queueFunction(queueHandler.eventQueue, message, targetButton.name)

			Timer(0.1, speakState).start()
