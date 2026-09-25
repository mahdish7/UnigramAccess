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

MEDIA_VIEWER_IDS = frozenset({
	"Photo", "ZoomOut", "ZoomIn", "VolumeButton", "Recognize",
	"MediaViewer", "MediaView", "ImageViewer", "VideoPlayer"
})


class UnigramMedia:
	def __init__(self, appModule):
		self.appModule = appModule
		self.saved_slider_focus = None
		self.active_slider = None
		self.last_progress_percentage = None
		self._is_monitoring_download = False

	def script_voiceMessageAcceleration(self, gesture):
		elements = self.appModule.ui_helper.getElements()
		targetButton = next((item for item in elements if getattr(item, "role", None) == Role.BUTTON and getattr(item, "UIAAutomationId", "") == "SpeedButton"), False)
		if not targetButton and elements and getattr(elements[0], "role", None) == Role.WINDOW:
			targetButton = next((item for item in getattr(elements[0], "children", []) if getattr(item, "role", None) == Role.BUTTON and getattr(item, "UIAAutomationId", "") == "SpeedButton"), False)
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
		except Exception as e:
			log.debugException(f"Swallowed exception: {e}")
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
		except Exception as e:
			log.debugException(f"Swallowed exception: {e}")
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
			except Exception as e:
				log.debugException(f"Swallowed exception: {e}")
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
				except Exception as e:
					log.debugException(f"Swallowed exception: {e}")
			message(_("The audio player has been closed"))
		else:
			message(_("Nothing is playing right now"))

	def script_pauseVoiceMessage(self, gesture):
		targetButton = next((item for item in self.appModule.ui_helper.getElements() if item.role == Role.BUTTON and item.UIAAutomationId == "PlaybackButton"), False)
		if targetButton:
			lastFocus = api.getFocusObject()
			targetButton.doAction()
			if lastFocus:
				try:
					lastFocus.setFocus()
				except Exception as e:
					log.debugException(f"Swallowed exception: {e}")
		else: message(_("Nothing is playing right now"))

	def _safe_set_focus(self, candidate):
		"""Safely set focus to candidate or its focusable child using standard NVDA API."""
		if not candidate:
			return False
		try:
			if not getattr(candidate, "parent", None):
				return False
			if getattr(candidate, "isFocusable", True):
				try:
					candidate.setFocus()
					return True
				except Exception as e:
					log.debugException(f"Swallowed exception: {e}")
			first = getattr(candidate, "firstChild", None)
			if first and getattr(first, "isFocusable", True):
				try:
					first.setFocus()
					return True
				except Exception as e:
					log.debugException(f"Swallowed exception: {e}")
		except Exception as e:
			log.debugException(f"Swallowed exception: {e}")
		return False

	def is_media_popup_element(self, obj):
		"""Check if an NVDA object is inside the full-screen media viewer popup."""
		if not obj:
			return False
		try:
			role = getattr(obj, "role", None)
			if role in (Role.MENU, Role.MENUITEM, Role.POPUPMENU):
				return False
			auto_id = getattr(obj, "UIAAutomationId", "") or ""
			if auto_id in MEDIA_VIEWER_IDS:
				return True
			if auto_id in ("TextField", "ChatsList", "SearchField", "Message_item"):
				return False
			if self.appModule.ui_helper.is_message_object(obj):
				return False

			curr = obj
			depth = 0
			while curr and depth < 8:
				if not getattr(curr, "parent", None) or getattr(curr, "role", None) in (Role.WINDOW, Role.DIALOG):
					break
				curr_id = getattr(curr, "UIAAutomationId", "") or ""
				if curr_id in MEDIA_VIEWER_IDS:
					return True
				raw_name = getattr(curr, "name", None) or getattr(curr, "windowText", None)
				if raw_name:
					clean_name = str(raw_name).strip().strip("\u200e\u200f\u202a\u202b\u202c").lower()
					if clean_name == "popup" or curr_id == "Popup":
						if getattr(curr, "role", None) not in (Role.MENU, Role.POPUPMENU):
							return True
				curr = getattr(curr, "parent", None)
				depth += 1
		except Exception as e:
			log.debugException(f"Swallowed exception: {e}")
		return False

	def handle_media_step(self, obj):
		"""Advance the media focus state machine from real UI focus events."""
		if not (self.appModule.isMedia and isinstance(self.appModule.isMedia, dict)):
			return False

		dismiss_source = self.appModule.isMedia.get("confirmed_dismissal")
		if dismiss_source:
			# If focus is still inside the popup, dialog has not closed yet
			if self.is_media_popup_element(obj):
				return False

			log.debug(f"Media viewer: closed via {dismiss_source}, restoring focus")
			target = self.appModule.isMedia.get("initial_obj")
			if not target or not getattr(target, "parent", None):
				target = self.appModule.saved_items.get("last focus object")
			self.appModule.isMedia = False

			if target and getattr(target, "parent", None):
				log.debug(f"Media viewer: restoring focus to target role={getattr(target, 'role', None)}")
				return self._safe_set_focus(target)

			return False

		# Dismissal not requested yet: check if media viewer has opened
		if self.is_media_popup_element(obj):
			if not self.appModule.isMedia.get("is_open"):
				self.appModule.isMedia["is_open"] = True
				log.debug("Media viewer: popup element confirmed open")
			return False

		# Dismissal not confirmed yet: media opened or playing
		if obj == self.appModule.isMedia.get("initial_obj"):
			return False

		# If media was triggered but focus moved to another element without opening viewer:
		if not self.appModule.isMedia.get("is_open"):
			self.appModule.isMedia = False
			return False

		return False

	def script_actionMediaInMessage(self, gesture):
		obj = api.getFocusObject()
		if not self.appModule.ui_helper.is_message_object(obj):
			gesture.send()
			return

		if self.appModule.isMessageSelectionMode:
			gesture.send()
			return

		targetButton = None
		if getattr(obj, "media", None):
			targetButton = next((item for item in obj.media.children if item.role in (Role.LINK, Role.BUTTON) and item.UIAAutomationId == "Button"), None)
		else:
			item = obj.firstChild
			while item:
				if item.role in (Role.LINK, Role.BUTTON) and item.UIAAutomationId == "Button":
					targetButton = item
					break
				item = item.next

		if not targetButton:
			gesture.send()
			return

		self.appModule.saved_items.save("last focus object", obj)
		self.appModule.isMedia = {
			"initial_obj": obj,
			"is_open": False,
			"confirmed_dismissal": None,
		}
		log.debug("Media: action triggered")
		targetButton.doAction()

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
			except Exception as e:
				log.debugException(f"Swallowed exception: {e}")
		return True

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
				except Exception as e:
					log.debugException(f"Swallowed exception: {e}")
			return

		# Find the slider
		slider = self._find_voice_slider()

		if slider:
			self.saved_slider_focus = current_focus
			self.active_slider = slider
			try:
				slider.setFocus()
			except Exception as e:
				log.debugException(f"Swallowed exception: {e}")

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
						except Exception as e:
							log.debugException(f"Swallowed exception: {e}")
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
		if not conf.get("voiceDownloadProgress"):
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
			if not conf.get("voiceDownloadProgress"):
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
