# -*- coding:utf-8 -*-
import addonHandler
addonHandler.initTranslation()
from controlTypes import Role, State
import api
from ui import message
import speech
import core
from nvwave import playWaveFile
import os
import queueHandler
from .unigram_logger import ulog as log
from .cnf import conf
from .unigram_utils import isActivelyDownloading

baseDir = os.path.join(os.path.dirname(__file__), "media")

class UnigramMedia:
	def __init__(self, appModule):
		self.appModule = appModule
		self.saved_slider_focus = None
		self.active_slider = None
		self.last_progress_percentage = None
		self._is_monitoring_download = False

	def script_voiceMessageAcceleration(self, gesture):
		targetButton = next((item for item in self.appModule.ui_helper.getElements() if item.role == Role.BUTTON and item.UIAAutomationId == "SpeedButton"), False)
		if not targetButton and self.appModule.ui_helper.getElements()[0].role == Role.WINDOW:
			targetButton = next((item for item in self.appModule.ui_helper.getElements()[0].children if item.role == Role.BUTTON and item.UIAAutomationId == "SpeedButton"), False)
		if targetButton: targetButton.doAction()
		else: message(_("Nothing is playing right now"))

	def _is_slider_element(self, obj):
		try:
			if not obj:
				return False
			if getattr(obj, 'role', None) in (Role.UNKNOWN, Role.SLIDER) and getattr(obj, 'UIAAutomationId', None) == "Slider":
				return True
			parent = getattr(obj, 'parent', None)
			if parent and getattr(parent, 'role', None) in (Role.UNKNOWN, Role.SLIDER) and getattr(parent, 'UIAAutomationId', None) == "Slider":
				return True
			return False
		except Exception:
			return False


	def _is_slider_alive(self, slider):
		if not slider:
			return False
		try:
			loc = slider.location
			if not loc or loc.width <= 0 or loc.height <= 0:
				return False
			states = getattr(slider, 'states', set())
			if State.INVISIBLE in states or State.UNAVAILABLE in states or State.OFFSCREEN in states:
				return False
			_ = slider.name
			return True
		except Exception:
			return False

	def _find_voice_slider(self):
		slider = self.appModule.saved_items.get("slider")
		if self._is_slider_alive(slider):
			return slider

		elements = self.appModule.ui_helper.getElements()
		for item in elements:
			if self._is_slider_element(item) and self._is_slider_alive(item):
				self.appModule.saved_items.save("slider", item)
				return item

		if elements and elements[0].role == Role.WINDOW:
			try:
				for item in elements[0].children:
					if self._is_slider_element(item) and self._is_slider_alive(item):
						self.appModule.saved_items.save("slider", item)
						return item
			except Exception:
				pass
		return None

	def script_closingVoiceMessage(self, gesture):
		slider = self._find_voice_slider()
		targetButton = slider.previous if (slider and slider.previous and slider.previous.role == Role.BUTTON) else None
		if targetButton:
			lastFocus = api.getFocusObject()
			targetButton.doAction()
			if lastFocus:
				try:
					lastFocus.setFocus()
				except Exception:
					pass
			message(_("The audio player has been closed"))
		else:
			message(_("Nothing is playing right now"))

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
				self.appModule.isExitFromMedia = True
		core.callLater(100, spechState)

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

	def get_elapsed_label(self):
		"""Find ElapsedLabel indicating active voice recording."""
		for item in reversed(self.appModule.ui_helper.getElements()):
			if getattr(item, "UIAAutomationId", None) == "ElapsedLabel":
				return item
		return None

	def is_voice_recording(self):
		"""Check if voice recording is currently active."""
		return bool(self.get_elapsed_label())

	def cancel_voice_recording(self, gesture):
		"""Cancel an ongoing voice recording."""
		indicator = conf.get("voiceMessageRecordingIndicator")
		if indicator == "audio":
			playWaveFile(os.path.join(baseDir, "cancel_voice_message_recording.wav"))
		elif indicator == "text":
			message(_("Recording canceled"))
		gesture.send()
		last_focus = api.getFocusObject()
		if last_focus:
			try:
				last_focus.setFocus()
			except Exception:
				pass
		return True

	def cycle_voice_recording_indicator(self):
		"""Cycle notification mode between none, text, and audio."""
		current = conf.get("voiceMessageRecordingIndicator")
		if current == "none":
			conf.set("voiceMessageRecordingIndicator", "text")
			message(_("Voice recording notifications set to text"))
		elif current == "text":
			conf.set("voiceMessageRecordingIndicator", "audio")
			message(_("Voice recording notifications set to sounds"))
		elif current == "audio":
			conf.set("voiceMessageRecordingIndicator", "none")
			message(_("Recording voice messages has standard behavior"))

	def script_cancelVoiceMessageRecording(self, gesture):
		"""Delegate to AppModule dispatcher for backward compatibility."""
		return self.appModule.script_cancelVoiceMessageRecording(gesture)

	def script_toggleVoiceSlider(self, gesture):
		current_focus = api.getFocusObject()

		if self._is_slider_element(current_focus):
			# We are on the slider, jump back
			saved_focus = getattr(self, 'saved_slider_focus', None)
			self.saved_slider_focus = None
			self.active_slider = None
			if saved_focus:
				try:
					saved_focus.setFocus()
				except Exception:
					pass
			return

		# Find the slider
		slider = self._find_voice_slider()

		if slider:
			self.saved_slider_focus = current_focus
			self.active_slider = slider
			try:
				slider.setFocus()
			except Exception:
				pass

			def monitor_slider():
				# Stop if saved focus is cleared (e.g. user toggled back manually via Alt+S)
				if not getattr(self, 'saved_slider_focus', None):
					return

				# Check if slider is still on screen and alive
				if self._is_slider_alive(slider):
					curr = api.getFocusObject()
					if self._is_slider_element(curr):
						# User is still focused on the slider, continue monitoring
						core.callLater(300, monitor_slider)
					else:
						# User manually navigated focus away while voice was still playing
						self.saved_slider_focus = None
						self.active_slider = None
						return
				else:
					# Slider is closed/gone (voice finished playing or player closed)
					speech.cancelSpeech()
					saved_focus = getattr(self, 'saved_slider_focus', None)
					self.saved_slider_focus = None
					self.active_slider = None
					if saved_focus:
						try:
							saved_focus.setFocus()
						except Exception:
							pass
					return

			core.callLater(300, monitor_slider)
		else:
			message(_("Slider not found"))


	def waiting_for_recognition(self, obj):
		interval = .5
		def tick(obj):
			if not obj or not obj.next: return
			if obj.next.UIAAutomationId == "RecognizedText" and obj.next.name:
				def speak_result():
					if obj and obj.next: text = obj.next.name
					else: text = ""
					queueHandler.queueFunction(queueHandler.eventQueue, message, text)
				core.callLater(400, speak_result)
				try: playWaveFile(os.path.join(baseDir, "RecognitionFinish.wav"))
				except Exception: pass
				return
			else: 
				core.callLater(int(interval * 1000), tick, obj)
		core.callLater(int(interval * 1000), tick, obj)

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
			except Exception: message(_("Conversion started"))
			self.waiting_for_recognition(button)
		else: message(_("Button not found"))

	def start_download_monitoring(self, obj):
		"""Poll download progress in real time (500ms) while focus remains on the actively downloading media button."""
		if conf.get("voicingPerformanceIndicators") == "none":
			return
		if not obj or getattr(obj, "UIAAutomationId", "") not in ("Button", "Download"):
			return

		if not isActivelyDownloading(getattr(obj, "name", "")):
			return

		if getattr(self, "_is_monitoring_download", False):
			return

		self._is_monitoring_download = True
		self.last_progress_percentage = None

		def monitor():
			if conf.get("voicingPerformanceIndicators") == "none":
				self._is_monitoring_download = False
				return

			curr = api.getFocusObject()
			if curr != obj:
				self._is_monitoring_download = False
				return

			if not isActivelyDownloading(getattr(curr, "name", "")):
				self._is_monitoring_download = False
				return

			val = getattr(curr, "value", None)
			if val is not None:
				try:
					clean_val = int(float(str(val).strip("% ")))
				except (ValueError, TypeError):
					clean_val = None

				if clean_val is not None and clean_val != self.last_progress_percentage:
					if self.last_progress_percentage is not None:
						speech.cancelSpeech()
					self.last_progress_percentage = clean_val
					message(f"{clean_val}%")
					if clean_val >= 100:
						self._is_monitoring_download = False
						return

			core.callLater(500, monitor)

		core.callLater(500, monitor)
