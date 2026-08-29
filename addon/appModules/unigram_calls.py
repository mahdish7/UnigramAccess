# -*- coding:utf-8 -*-
import addonHandler
addonHandler.initTranslation()
from controlTypes import Role, State
from ui import message
import api
import queueHandler
from threading import Timer

class UnigramCalls:
	def __init__(self, appModule):
		self.appModule = appModule

	def script_call(self, gesture):
		try: targetButton = next((item for item in self.appModule.ui_helper.getElements() if (item.role == Role.BUTTON and item.UIAAutomationId == "Call") or (item.role == Role.LINK and item.UIAAutomationId == "GroupCall") or (item.next and item.next.UIAAutomationId == "Audio" and item.firstChild and item.firstChild.UIAAutomationId == "TitleInfo") ), False)
		except Exception: targetButton =False
		if targetButton: targetButton.doAction()
		else: message(_("Call unavailable"))

	def script_videoCall(self, gesture):
		targetButton = next((item for item in self.appModule.ui_helper.getElements() if item.role == Role.BUTTON and item.UIAAutomationId == "VideoCall"), False)
		if targetButton: targetButton.doAction()
		else: message(_("Video call not available"))

	def script_callCancellation(self, gesture):
		targetButton = next((item for item in self.appModule.ui_helper.getElements()[1:] if (item.UIAAutomationId == "Accept" and item.previous and item.previous.UIAAutomationId == "Audio") or (item.UIAAutomationId == "Leave" and item.firstChild and item.firstChild.name == "\ue711") or (item.previous and item.previous.UIAAutomationId == "Audio" and item.firstChild and item.firstChild.name == "\ue711")), False)
		if targetButton:
			lastFocus = api.getFocusObject()
			message(targetButton.name)
			self.appModule.fixedDoAction(targetButton)
			lastFocus.setFocus()

	def script_microphone(self, gesture):
		obj = api.getFocusObject()
		targetButton = False
		isVoiceChat = False
		for item in self.appModule.ui_helper.getElements():
			if item.UIAAutomationId == "Audio" and item.previous and item.previous.UIAAutomationId == "Video" and item.next and item.next.UIAAutomationId == "Accept":
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
				def spechState(): queueHandler.queueFunction(queueHandler.eventQueue, message, targetButton.next.name)
				Timer(.1, spechState).start()
				return True
			self.appModule.fixedDoAction(targetButton)
			obj.setFocus()
			def spechState(): queueHandler.queueFunction(queueHandler.eventQueue, message, targetButton.name)
			Timer(.1, spechState).start()

	def script_video(self, gesture):
		obj = api.getFocusObject()
		targetButton = False
		isVoiceChat = False
		for item in self.appModule.ui_helper.getElements():
			if item.UIAAutomationId == "Video" and item.next.UIAAutomationId == "Audio" and item.next.next.UIAAutomationId == "Accept":
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
				def spechState():
					if targetButton.firstChild.name == "\ue964": queueHandler.queueFunction(queueHandler.eventQueue, message, _("Camera on"))
					elif targetButton.firstChild.name == "\ue963": queueHandler.queueFunction(queueHandler.eventQueue, message, _("Camera off"))
				Timer(.1, spechState).start()
				return
			self.appModule.fixedDoAction(targetButton)
			obj.setFocus()
			def spechState(): queueHandler.queueFunction(queueHandler.eventQueue, message, targetButton.name)
			Timer(.1, spechState).start()
