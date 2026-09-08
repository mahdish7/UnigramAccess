# -*- coding:utf-8 -*-
# UnigramAccess: Message and chat element formatting logic.

import re

import addonHandler
from controlTypes import Role, State
import queueHandler
from ui import message

addonHandler.initTranslation()

from .cnf import conf
from .data import (
	keywordsInMessages,
	labels_for_buttons,
	labels_in_buttons,
	phrase_administrator_in_message,
)
from .unigram_logger import ulog as log
from .unigram_utils import isActivelyDownloading


def formatMessageOnFocus(obj, savedItems):
	"""Format and enrich the name of a message when it receives focus.

	Handles polls, link descriptions, voice message durations, call durations,
	sender name prefixes, read/unread status, admin badges, and selection state.
	"""
	log.info("Processing focused message.")
	keywords = obj.keywords
	sender = ""
	header = False
	senderMessage = getattr(obj, "sender_message", "")

	if isPollMessage(obj):
		formatPollMessage(obj)

	item = obj.firstChild
	while item:
		if (
			conf.get("actionDescriptionForLinks")
			and item.role == Role.LINK
			and len(item.name) > 30
			and not item.UIAAutomationId
			and item.firstChild.UIAAutomationId == "Label"
		):
			# Processing the description of the link contained in the message
			description = item.name.strip()
			if not conf.get("voiceFullDescriptionOfLinkToYoutube") and description.startswith("YouTube "):
				description = description.split("\n")
				description = "\n".join(description[:2])
			# Escape all backslash symbols
			description = description.replace("\\", "").replace("http:\\", "\\\\")
			obj.name = re.sub(
				r"[.,]?{}|{}".format(keywords[3], keywords[2]),
				r". \n{}\g<0>".format(description),
				obj.name,
			)
			obj.name = re.sub(r"(https?://\S+)\?[^\s,]+", r"\g<1>", obj.name)

		elif item.UIAAutomationId == "Subtitle" and len(item.name) < 15 and " / " in item.name:
			# Checking if a message is a voice message
			obj.name = item.name + ", " + obj.name.replace(item.name[-5:], "")

		elif item.UIAAutomationId == "HeaderLabel":
			header = item

		item = item.next

	# Checking if a message is a call
	try:
		if (
			obj.firstChild.role == Role.LINK
			and not obj.firstChild.name
			and obj.childCount == 7
			and obj.children[1].UIAAutomationId == "TitleLabel"
			and obj.children[3].role == Role.STATICTEXT
		):
			a = obj.children[1].name
			b = ",".join(obj.children[3].name.split(",")[1:])
			obj.name = obj.name.replace(a, a + b)
			obj.index_last_part_in_message += len(b)
	except Exception:
		pass

	# Checking whether to add a message sender name
	profileName = savedItems.get("profile name")
	if conf.get("saySenderName") in ("sent", "all") and senderMessage == "send" and not header:
		sender = _("You") + ".\n"
	elif (
		conf.get("saySenderName") in ("received", "all")
		and profileName
		and obj.simpleFirstChild.UIAAutomationId not in ("Photo", "1HeaderLabel", "PhotoRoot")
		and obj.simpleFirstChild.location.left - obj.location.left < 35
		and not header
	):
		sender = profileName.firstChild.name + ".\n"

	# Check the status of the message — read or not read (only for sent messages)
	if keywords[0] in getattr(obj, "end_text", ""):
		# If the message is read, delete information about it
		obj.name = obj.name.replace(keywords[0], ".", -1)
	elif keywords[1] in getattr(obj, "end_text", ""):
		# If the message is not read, check whether it is necessary to display info
		if senderMessage == "received" or (profileName and profileName.childCount == 1):
			obj.name = obj.name.replace(keywords[1], ".", -1)
		elif conf.get("unreadBeforeMessageContent"):
			obj.name = obj.name.replace(keywords[1], ".", -1)
			obj.name = keywords[1][2:] + ". " + obj.name

	if not conf.get("announce_end_of_message") and obj.index_last_part_in_message:
		obj.name = obj.name[:obj.index_last_part_in_message]

	if keywords[3] in getattr(obj, "end_text", ""):
		# Removal of the phrase "administrator" and the phrase "owner" in messages
		listText = obj.name.split("\n")
		keyPhrases = phrase_administrator_in_message.get(conf.get("lang"), phrase_administrator_in_message["en"])
		enKeyPhrases = phrase_administrator_in_message["en"]
		if (
			not conf.get("notify administrators in messages")
			and len(listText) > 1
			and listText[1] in (
				", " + keyPhrases[0] + ". \r",
				", " + keyPhrases[1] + ". \r",
				", " + enKeyPhrases[0] + ". \r",
				", " + enKeyPhrases[1] + ". \r",
			)
		):
			del listText[1]
			obj.name = "\n".join(listText)

	obj.name = sender + obj.name

	# Check if a message is selected
	if State.SELECTED in obj.states:
		obj.name = _("Selected") + ". " + obj.name

	return obj.name


def formatChatElementOnFocus(obj):
	"""Reorder or strip chat type prefix relative to chat name based on user config.

	Handles 'beforeName', 'afterName', and "don'tVoice" modes.
	"""
	# If the user does not want to change the order, return immediately for speed
	if conf.get("voiceTypeAfterChatName") == "beforeName":
		return obj.name

	item = obj.firstChild
	while item:
		if item.UIAAutomationId == "TitleLabel":
			title = item.name
			chatType = obj.name.split(", ")[0] if not obj.name.startswith(title) else ""
			if not chatType:
				break
			elif conf.get("voiceTypeAfterChatName") == "afterName":
				obj.name = obj.name.replace(chatType + ", " + title, title + ", " + chatType, 1)
			elif conf.get("voiceTypeAfterChatName") == "don'tVoice":
				obj.name = obj.name.replace(chatType + ", ", "", 1)
			break
		item = item.next

	return obj.name


def isPollMessage(obj) -> bool:
	"""Check if an NVDAObject represents a poll or quiz message."""
	if not obj or not hasattr(obj, "children"):
		return False
	children = obj.children or []
	has_type = any(getattr(c, "UIAAutomationId", "") == "Type" for c in children)
	has_poll_items = any(
		c.role == Role.TOGGLEBUTTON or getattr(c, "UIAAutomationId", "") == "Votes"
		for c in children
	)
	return has_type and has_poll_items


def formatPollMessage(obj) -> str:
	"""Enrich a poll message with explanation and details if present."""
	try:
		children = obj.children or []
		text_blocks_before_type = []
		type_name = ""
		for child in children:
			auto_id = getattr(child, "UIAAutomationId", "")
			if auto_id == "Type":
				type_name = child.name.strip() if child.name else ""
				break
			if auto_id == "TextBlock" or child.role == Role.STATICTEXT:
				val = child.name.strip() if child.name else ""
				if val:
					text_blocks_before_type.append(val)

		# If there are 2 or more TextBlocks before Type, the preceding ones are
		# the Explanation (توضیحات) and the last one is the Question.
		if len(text_blocks_before_type) >= 2:
			explanation = "\n".join(text_blocks_before_type[:-1])
			question = text_blocks_before_type[-1]
			# Translators: Label for the explanation/description of a poll or quiz.
			explanation_text = f"{_('Explanation')}: {explanation}"

			if question and question in obj.name:
				obj.name = obj.name.replace(question, f"{question}. {explanation_text}")
			elif type_name and type_name in obj.name:
				obj.name = obj.name.replace(type_name, f"{type_name}. {explanation_text}")
			else:
				obj.name = f"{explanation_text}. {obj.name}"
	except Exception as e:
		log.error(f"Error formatting poll message: {e}")
	return obj.name


def formatPollOption(obj) -> str:
	"""Format a focused poll answer option toggle button."""
	try:
		children = obj.children or []
		for child in children:
			if child.name == "\uf13e":
				# Translators: Label prepended to the correct answer in quiz polls.
				prefix = _("Right answer") + ": "
				if not obj.name.startswith(prefix):
					obj.name = prefix + obj.name
				break
	except Exception as e:
		log.error(f"Error formatting poll option: {e}")
	return obj.name


def announceFolderChange(obj, savedItems):
	"""Announce folder name and unread chat counts when switching chat folders."""
	tabItems = obj.name.split(", ")
	countChats = None
	lastSelectedFolder = savedItems.get("last selected folder")

	if lastSelectedFolder != tabItems[0]:
		savedItems.save("last selected folder", tabItems[0])
		if len(tabItems) > 1 and tabItems[1] != "0":
			countChats = tabItems[1]
	else:
		return False

	text = savedItems.get("last selected folder")
	if countChats:
		text += ", " + countChats
	queueHandler.queueFunction(queueHandler.eventQueue, message, text)


def resolveUnlabeledElement(obj):
	"""Assign a human-readable name to unlabeled UI elements.

	Checks icon glyph dictionaries, automation IDs, and child element names
	to produce a meaningful label.
	"""
	if obj.firstChild and obj.firstChild.name in labels_in_buttons:
		obj.name = labels_in_buttons[obj.firstChild.name]
	elif obj.UIAAutomationId in labels_for_buttons:
		obj.name = labels_for_buttons[obj.UIAAutomationId]
	elif obj.UIAAutomationId:
		obj.name = "".join(" " + char.lower() if char.isupper() else char for char in obj.UIAAutomationId)
		obj.name = "".join(obj.name[1:]).capitalize()
	elif obj.childCount > 1:
		name = [item.name for item in obj.children if item.name != ""]
		obj.name = "/. ".join(name)


def formatMediaButtonName(obj, raw_name=""):
	"""Append file/media name and size or duration to the raw media button name."""
	if not raw_name:
		raw_name = getattr(obj, "name", "") or ""

	base_name = raw_name.split(": ")[0] if ": " in raw_name else raw_name
	if not conf.get("voiceMediaButtonDetails") or isActivelyDownloading(base_name):
		return base_name

	parent = getattr(obj, "parent", None)
	if not parent:
		return base_name
	children = getattr(parent, "children", [])
	title_elem = next((item for item in children if getattr(item, "UIAAutomationId", "") == "Title"), None)
	trim_elem = next((item for item in children if getattr(item, "UIAAutomationId", "") == "TitleTrim"), None)
	subtitle_elem = next((item for item in children if getattr(item, "UIAAutomationId", "") == "Subtitle"), None)
	if not subtitle_elem:
		overlay = next((item for item in children if getattr(item, "UIAAutomationId", "") == "Overlay"), None)
		if overlay and getattr(getattr(overlay, "firstChild", None), "UIAAutomationId", "") == "Subtitle":
			subtitle_elem = overlay.firstChild

	title = ""
	if title_elem and getattr(title_elem, "name", ""):
		title = title_elem.name.strip()
		if trim_elem and getattr(trim_elem, "name", ""):
			title += trim_elem.name.strip()

	subtitle = getattr(subtitle_elem, "name", "").strip() if subtitle_elem else ""

	details = []
	if title:
		details.append(title)
	if subtitle:
		details.append(subtitle)

	if details:
		summary = ", ".join(details)
		return f"{base_name}: {summary}" if base_name else summary
	return base_name


def formatMediaButtonOnFocus(obj):
	"""Append file/media name and size or duration to the media button label."""
	if not conf.get("voiceMediaButtonDetails"):
		return
	obj.name = formatMediaButtonName(obj, getattr(obj, "name", "") or "")
