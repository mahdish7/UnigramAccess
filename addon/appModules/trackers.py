# -*- coding:utf-8 -*-
# State tracking and caching logic

from threading import Timer
from ui import message
import queueHandler
import api

import addonHandler
addonHandler.initTranslation()

from .data import *
from .cnf import conf, lang



class Saved_items:
	# store frequently used window elements in cache for faster access
	_items = {}
	def get(self, key):
		id = api.getFocusObject().windowHandle
		try: return self._items[id][key]
		except Exception: return False
	def save(self, key, obj):
		# id = obj.windowHandle
		id = api.getFocusObject().windowHandle
		if id not in self._items: self._items[id] = {}
		self._items[id][key] = obj


class Title_change_tracking:
	active = False
	pause = False
	interval = .5
	saved_items = False
	@classmethod
	def tick(cls):
		if not cls.active or cls.pause: return
		title = cls.saved_items.get("profile name")
		if not title or not title.isInForeground:
			cls.pause = True
			return False
		last_profile_name = cls.saved_items.get("last profile name") or ("",)
		if title.childCount > 1 and title.lastChild.name != last_profile_name[-1]:
			if title.firstChild.name == last_profile_name[0]:
				# Announce changes only if these changes are not related to switching to another chat
				text = title.lastChild.name
				queueHandler.queueFunction(queueHandler.eventQueue, message, text)
			new_title = [item.name for item in title.children]
			cls.saved_items.save("last profile name", new_title)
		Timer(cls.interval, cls.tick).start()
	@classmethod
	def toggle(cls, saved_items=False):
		if not conf.get("automatically announce activity in chats") or not saved_items:
			cls.saved_items = saved_items
			cls.active = True
			cls.pause = False
			conf.set("automatically announce activity in chats", True)
			Timer(cls.interval, cls.tick).start()
			return True
		else:
			cls.active = False
			conf.set("automatically announce activity in chats", False)
			return False
	@classmethod
	def restore(cls, saved_items=False):
		cls.pause = False
		cls.active = True
		cls.saved_items = saved_items
		cls.saved_items.save("last profile name", None)
		Timer(cls.interval, cls.tick).start()


class Chat_update:
	active = False
	pause = False
	interval = .3
	app = False
	@classmethod
	def tick(cls):
		if not cls.active or cls.pause: return
		try : last_message = cls.app.getMessagesElement().lastChild
		except Exception: last_message = False
		if not last_message or not last_message.isInForeground:
			cls.pause = True
			return False
		# The first item is the name of the chat in which the last message was recorded
		# The second item is the message index
		last_saved_message = cls.app.saved_items.get("last message") or ("", "")
		# If there is a problem getting the message index, terminate the function and call the next iteration
		try:
			last_message.positionInfo["indexInGroup"]
			last_message.positionInfo["similarItemsInGroup"]
		except Exception:
			Timer(cls.interval, cls.tick).start()
			return
		if last_message.positionInfo["indexInGroup"] != last_saved_message[1] and last_message.positionInfo["indexInGroup"] == last_message.positionInfo["similarItemsInGroup"]:
			try:
				title = cls.app.saved_items.get("profile name").firstChild.name
			except Exception:
				title = False
			keywords = keywordsInMessages.get(conf.get("lang"), keywordsInMessages["en"])
			if ((title == last_saved_message[0]) or not title) and keywords[3] in last_message.name[-60:]:
				text = cls.app.action_message_focus(last_message.firstChild)
				queueHandler.queueFunction(queueHandler.eventQueue, message, text)
			try:
				new_message = (title, last_message.positionInfo["indexInGroup"])
				cls.app.saved_items.save("last message", new_message)
			except Exception: pass
		Timer(cls.interval, cls.tick).start()
	@classmethod
	def toggle(cls, app=False):
		if not conf.get("automatically announce new messages") or not app:
			cls.active = True
			conf.set("automatically announce new messages", True)
			cls.app = app
			Timer(cls.interval, cls.tick).start()
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
		Timer(cls.interval, cls.tick).start()
