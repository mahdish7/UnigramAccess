# -*- coding:utf-8 -*-
# UnigramAccess: Background polling trackers and element caching.

import api
import core
import queueHandler
from ui import message

import addonHandler

addonHandler.initTranslation()

from .cnf import conf
from .data import keywordsInMessages


class Saved_items:
	"""Window-handle-keyed cache for frequently accessed UI elements.

	Avoids repeated expensive UIA tree traversals by storing references to
	elements like profile name, chats list, messages list, and slider.
	"""

	_items = {}

	def get(self, key):
		import comtypes
		windowId = api.getFocusObject().windowHandle
		try:
			obj = self._items[windowId][key]
			if hasattr(obj, "name"):
				_ = obj.name
			return obj
		except comtypes.COMError:
			del self._items[windowId][key]
			return False
		except Exception:
			return False

	def save(self, key, obj):
		windowId = api.getFocusObject().windowHandle
		if windowId not in self._items:
			self._items[windowId] = {}
		self._items[windowId][key] = obj


class Title_change_tracking:
	"""Polling loop that monitors chat title/status changes.

	Detects typing indicators, online/offline transitions, and member count
	updates in the foreground chat, announcing them to the user.
	Uses core.callLater with a 500 ms interval.
	"""

	active = False
	pause = False
	interval = 0.5
	savedItems = False

	@classmethod
	def tick(cls):
		if not cls.active or cls.pause:
			return
		title = cls.savedItems.get("profile name")
		if not title or not title.isInForeground:
			cls.pause = True
			return False
		lastProfileName = cls.savedItems.get("last profile name") or ("",)
		if title.childCount > 1 and title.lastChild.name != lastProfileName[-1]:
			if title.firstChild.name == lastProfileName[0]:
				# Announce changes only if not related to switching to another chat
				text = title.lastChild.name
				queueHandler.queueFunction(queueHandler.eventQueue, message, text)
			newTitle = [item.name for item in title.children]
			cls.savedItems.save("last profile name", newTitle)
		core.callLater(int(cls.interval * 1000), cls.tick)

	@classmethod
	def toggle(cls, savedItems=False):
		if not conf.get("automatically announce activity in chats") or not savedItems:
			cls.savedItems = savedItems
			cls.active = True
			cls.pause = False
			conf.set("automatically announce activity in chats", True)
			core.callLater(int(cls.interval * 1000), cls.tick)
			return True
		else:
			cls.active = False
			conf.set("automatically announce activity in chats", False)
			return False

	@classmethod
	def restore(cls, savedItems=False):
		cls.pause = False
		cls.active = True
		cls.savedItems = savedItems
		cls.savedItems.save("last profile name", None)
		core.callLater(int(cls.interval * 1000), cls.tick)


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
