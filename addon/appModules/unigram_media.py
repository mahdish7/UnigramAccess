# -*- coding:utf-8 -*-
import addonHandler
addonHandler.initTranslation()
from controlTypes import Role, State
from keyboardHandler import KeyboardInputGesture
import api
from winBindings import user32 as winUser
import mouseHandler
from ui import message
import speech
from threading import Timer
from nvwave import playWaveFile
import os
import queueHandler
from logHandler import log
from .cnf import conf

baseDir = os.path.join(os.path.dirname(__file__), "media")

class UnigramMedia:
	def __init__(self, appModule):
		self.appModule = appModule

	def script_voiceMessageAcceleration(self, gesture):
		targetButton = next((item for item in self.appModule.ui_helper.getElements() if item.role == Role.BUTTON and item.UIAAutomationId == "SpeedButton"), False)
		if not targetButton and self.appModule.ui_helper.getElements()[0].role == Role.WINDOW:
			targetButton = next((item for item in self.appModule.ui_helper.getElements()[0].children if item.role == Role.BUTTON and item.UIAAutomationId == "SpeedButton"), False)
		if targetButton: targetButton.doAction()
		else: message(_("Nothing is playing right now"))

	def script_closingVoiceMessage(self, gesture, isMessage = True):
		targetButton = False
		for item in self.appModule.ui_helper.getElements()[1:]:
			try:
				if item.previous and item.previous.role == Role.TOGGLEBUTTON and item.previous.UIAAutomationId == "ShuffleButton":
					targetButton = item
					break
			except Exception:
				continue
		if targetButton:
			lastFocus = api.getFocusObject()
			targetButton.doAction()
			lastFocus.setFocus()
			message(_("The audio player has been closed"))
		else: message(_("Nothing is playing right now"))

	def script_pauseVoiceMessage(self, gesture):
		targetButton = next((item for item in self.appModule.ui_helper.getElements() if item.role == Role.BUTTON and item.UIAAutomationId == "PlaybackButton"), False)
		if targetButton:
			lastFocus = api.getFocusObject()
			targetButton.doAction()
			lastFocus.setFocus()
		else: message(_("Nothing is playing right now"))

	def script_actionMediaInMessage(self, gesture):
		obj = api.getFocusObject()
		message_states = obj.states
		gesture.send()
		if not self.appModule.ui_helper.is_message_object(obj): return
		def spechState():
			is_save_focus = True
			targetButton = None
			if obj.states != message_states: return
			if obj.media:
				targetButton = next((item for item in obj.media.children if item.role in (Role.LINK, Role.BUTTON) and item.UIAAutomationId == "Button"), None)
				if targetButton and targetButton.previous and targetButton.previous.UIAAutomationId != "Button": is_save_focus = False
			else:
				item = obj.firstChild
				while item:
					if item.role in (Role.LINK, Role.BUTTON) and item.UIAAutomationId == "Button":
						targetButton = item
						if item.location.width > 150: is_save_focus = False
						break
					item = item.next
			if not targetButton: return
			targetButton.doAction()
			if is_save_focus:
				obj.setFocus()
			else:
				self.appModule.is_exit_from_media = True
		Timer(.1, spechState).start()

	def script_recordingVoiceMessage(self, gesture):
		lastFocus = api.getFocusObject()
		if conf.get("voiceMessageRecordingIndicator") == "none":
			gesture.send()
			return
		obj = False
		log.debug("We got into the voice message recording function")
		lastFocus.setFocus()
		for item in reversed(self.appModule.ui_helper.getElements()):
			if item.role == Role.TOGGLEBUTTON and item.UIAAutomationId == "btnVoiceMessage":
				log.debug("Record voice message button found")
				obj = item
				break
			elif item.role == Role.BUTTON and item.UIAAutomationId in ("btnSendMessage", "btnEdit"):
				message(_("Recording a voice message will not be available until the edit field is empty"))
				return
		if not obj: return
		if obj.next and obj.next.UIAAutomationId == "ElapsedLabel":
			log.debug("Second press of the record voice message button")
			if conf.get("voiceMessageRecordingIndicator") == "audio":
				playWaveFile(os.path.join(baseDir, "send_voice_message.wav"))
			else:
				message(_("Record sent"))
		else:
			log.debug("First press of the record voice message button")
			if conf.get("voiceMessageRecordingIndicator") == "audio" and State.PRESSED in obj.states:
				playWaveFile(os.path.join(baseDir, "start_recording_video_message.wav"))
			elif conf.get("voiceMessageRecordingIndicator") == "audio":
				playWaveFile(os.path.join(baseDir, "start_recording_voice_message.wav"))
			elif conf.get("voiceMessageRecordingIndicator") == "text" and State.PRESSED in obj.states:
				message(_("Video"))
			else:
				message(_("Audio"))
		if conf.get("isFixedToggleButton"):
			log.debug("Standard button press")
			self.appModule.isSkipName = 1
			gesture.send()
		else:
			obj.doAction()
			lastFocus.setFocus()

	def script_cancelVoiceMessageRecording(self, gesture):
		import scriptHandler
		if scriptHandler.getLastScriptRepeatCount() == 1:
			if conf.get("voiceMessageRecordingIndicator") == "none":
				conf.set("voiceMessageRecordingIndicator", "text")
				message(_("Voice recording notifications set to text"))
			elif conf.get("voiceMessageRecordingIndicator") == "text":
				conf.set("voiceMessageRecordingIndicator", "audio")
				message(_("Voice recording notifications set to sounds"))
			elif conf.get("voiceMessageRecordingIndicator") == "audio":
				conf.set("voiceMessageRecordingIndicator", "none")
				message(_("Recording voice messages has standard behavior"))
			return
		if conf.get("voiceMessageRecordingIndicator") == "none":
			gesture.send()
			return
		obj = next((item for item in reversed(self.appModule.ui_helper.getElements()) if (item.UIAAutomationId == "ElapsedLabel") or (item.role == Role.BUTTON and item.UIAAutomationId == "ComposerHeaderCancel")), False)
		lastFocus = api.getFocusObject()
		if obj and obj.UIAAutomationId == "ComposerHeaderCancel":
			obj.doAction()
			lastFocus.setFocus()
			if obj.previous and obj.previous.name == "\uea4a": message(_("Reply canceled"))
			else: message(_("Edit canceled"))
		elif obj and obj.UIAAutomationId == "ElapsedLabel":
			if conf.get("voiceMessageRecordingIndicator") == "audio":
				playWaveFile(os.path.join(baseDir, "cancel_voice_message_recording.wav"))
			else:
				message(_("Recording canceled"))
		gesture.send()
		lastFocus.setFocus()
		lastFocus.setFocus()

	def rewind_voice_message(self, direction):
		slider = self.appModule.saved_items.get("slider")
		if not slider or slider.location.width == 0:
			message(_("Nothing is playing right now"))
			return False
		self.script_pauseVoiceMessage(None)
		obj = api.getFocusObject()
		slider.setFocus()
		KeyboardInputGesture.fromName(direction).send()
		self.script_pauseVoiceMessage(None)
		obj.setFocus()
		speech.cancelSpeech()
		obj.setFocus()

	def script_rewind_voice_message(self, gesture):
		try: index = int(gesture.mainKeyName[-1])
		except (AttributeError, ValueError): return
		slider = self.appModule.saved_items.get("slider")
		if not slider or slider.location.width == 0:
			message(_("Nothing is playing right now"))
			return False
		obj = api.getFocusObject()
		part = slider.location.width // 10
		x = slider.location.left + (part * index)
		y = slider.location.top + (slider.location.height // 2)
		winUser.dll.SetCursorPos(x, y)
		mouseHandler.executeMouseEvent(winUser.MOUSEEVENTF.LEFTDOWN, 0, 0)
		mouseHandler.executeMouseEvent(winUser.MOUSEEVENTF.LEFTUP, 0, 0)

	def script_rewindVoiceMessageForward(self, gesture):
		self.rewind_voice_message("rightArrow")

	def script_rewindVoiceMessageBack(self, gesture):
		self.rewind_voice_message("leftArrow")

	def waiting_for_recognition(self, obj):
		interval = .5
		def tick(obj):
			if not obj or not obj.next: return
			if obj.next.UIAAutomationId == "RecognizedText" and obj.next.name:
				def speak_result():
					if obj and obj.next: text = obj.next.name
					else: text = ""
					queueHandler.queueFunction(queueHandler.eventQueue, message, text)
				Timer(.4, speak_result).start()
				try: playWaveFile(os.path.join(baseDir, "RecognitionFinish.wav"))
				except Exception: pass
				return
			else: 
				Timer(interval, tick, [obj]).start()
		Timer(interval, tick, [obj]).start()

	def script_Recognize_voice_message(self, gesture):
		obj = api.getFocusObject()
		button = next((item for item in obj.children if item.UIAAutomationId == "Recognize"), None)
		if button:
			if State.PRESSED in button.states or button.next and button.next.UIAAutomationId == "RecognizedText":
				if button.next.UIAAutomationId == "RecognizedText" and button.next.name: message(_("This voice message is already converted to text"))
				elif button.next.UIAAutomationId == "RecognizedText" and button.next.name == "": message(_("Converting this voice message is already in process"))
				return
			button.doAction()
			obj.setFocus()
			try: playWaveFile(os.path.join(baseDir, "RecognitionStart.wav"))
			except Exception: message("Conversion started")
			self.waiting_for_recognition(button)
		else: message(_("Button not found"))
