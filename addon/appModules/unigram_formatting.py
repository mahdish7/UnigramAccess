# -*- coding:utf-8 -*-
# UnigramAccess: Message and chat element formatting logic.

import re

import addonHandler
from controlTypes import Role, State

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

# Precompiled dictionary and regex pattern for admin / owner badges across all supported languages
_ALL_ADMIN_BADGES = set()
for _pairs in phrase_administrator_in_message.values():
	for _p in _pairs:
		_clean = _p.strip().rstrip(".")
		if _clean:
			_ALL_ADMIN_BADGES.add(_clean)
_ALL_ADMIN_BADGES.update({
	"Admin", "Administrator", "Administrateur", "Administrador", "Amministratore",
	"Owner", "Creator", "Co-owner", "Moderator",
	"مدیر", "مالک", "سازنده", "ادمین", "مدیر کل", "هم‌بنیان‌گذار",
	"Владелец", "Администратор", "Адمین", "Создатель",
})
_ADMIN_BADGES_LOWER = {b.lower() for b in _ALL_ADMIN_BADGES}
_ADMIN_BADGES_PATTERN = re.compile(
	rf",\s*(?:{'|'.join(re.escape(b) for b in sorted(_ALL_ADMIN_BADGES, key=len, reverse=True))})\.?\s*\r?\n?",
	flags=re.IGNORECASE,
)


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
			and not getattr(item, "UIAAutomationId", "")
			and (
				len(getattr(item, "name", "") or "") > 30
				or (getattr(item, "name", "") or "").startswith("Link Preview:")
				or getattr(getattr(item, "firstChild", None), "UIAAutomationId", "") == "TitleLabel"
			)
		):
			raw_desc = (getattr(item, "name", "") or "").strip()
			# Language-independent stripping of link preview prefixes
			raw_desc = re.sub(
				r"^(?:Link Preview|پیش‌نمایش پیوند|پیش‌نمایش لینک|Предварительный просмотр):\s*",
				"",
				raw_desc,
				flags=re.IGNORECASE,
			)
			description = raw_desc

			if conf.get("cleanLinkDescriptions"):
				# Clean up standard YouTube boilerplate text if present
				if "Enjoy the videos and music you love" in description:
					description = description.replace("Enjoy the videos and music you love, upload original content, and share it all with friends, family, and the world on YouTube.", "").strip()
					if description.endswith(","):
						description = description[:-1].strip()

			# Escape all backslash symbols
			description = description.replace("\\", "").replace("http:\\", "\\\\")
			leading_prefix = keywords[4] if len(keywords) > 4 and keywords[4] else None
			if leading_prefix and leading_prefix in obj.name:
				target_pat = re.escape(leading_prefix)
			elif leading_prefix and "\u2068" in leading_prefix and leading_prefix.replace("\u2068", "") in obj.name:
				target_pat = re.escape(leading_prefix.replace("\u2068", ""))
			else:
				target_pat = r"[.,]?{}|{}".format(re.escape(keywords[3]), re.escape(keywords[2]))
			obj.name = re.sub(
				target_pat,
				r". \n{}\g<0>".format(description),
				obj.name,
			)
			if conf.get("cleanLinkDescriptions"):
				obj.name = re.sub(r"(https?://\S+)\?[^\s,]+", r"\g<1>", obj.name)

		elif item.UIAAutomationId == "Subtitle" and len(item.name) < 15 and " / " in item.name:
			# Checking if a message is a voice message
			obj.name = item.name + ", " + obj.name.replace(item.name[-5:], "")

		elif item.UIAAutomationId == "HeaderLabel":
			header = item

		item = item.next

	# Checking whether to add a message sender name
	profileName = savedItems.get("profile name")
	say_sender_mode = conf.get("saySenderName")

	if say_sender_mode in ("send", "all") and senderMessage == "send" and not header:
		sender = _("You") + ".\n"
	elif say_sender_mode in ("received", "all") and senderMessage == "received":
		# In group and channel chats, Unigram natively includes the author name
		# at the beginning of obj.name (e.g. "Author\r\n. Message text").
		# We must never prepend a sender name if obj.name already has one, nor
		# prepend the group title as a sender name.
		lines = obj.name.split("\n")
		has_sender_prefix = bool(
			header
			or (
				len(lines) > 1
				and (
					lines[1].startswith((", ", ". "))
					or lines[1].lstrip().startswith(".")
					or lines[1].strip().lower().lstrip(",").rstrip(".").strip() in _ADMIN_BADGES_LOWER
				)
			)
		)

		if not has_sender_prefix:
			# Check if message contains group visual markers (avatars / header labels)
			is_group_msg = any(
				getattr(c, "UIAAutomationId", "") in ("Photo", "PhotoRoot", "HeaderLabel")
				for c in getattr(obj, "children", [])
			)

			if not is_group_msg:
				# If profile button is not in cache, resolve it from the UI container
				if not profileName or not getattr(profileName, "location", None) or profileName.location.width == 0:
					appMod = getattr(obj, "appModule", None)
					if appMod and hasattr(appMod, "ui_helper"):
						profileName = next(
							(
								item
								for item in appMod.ui_helper.getElements()
								if getattr(item, "role", None) == Role.BUTTON and getattr(item, "UIAAutomationId", "") == "Profile"
							),
							None,
						)
						if profileName:
							savedItems.save("profile name", profileName)

				if profileName:
					is_group_profile = False
					try:
						if profileName.childCount > 1:
							sub = (getattr(profileName.lastChild, "name", "") or "").lower()
							if re.search(r"\d+\s*(?:member|subscriber|عضو|مشترک)", sub):
								is_group_profile = True
					except Exception as e:
						log.debugException(f"Swallowed exception: {e}")

					if not is_group_profile:
						partner_name = (
							getattr(getattr(profileName, "firstChild", None), "name", "")
							or getattr(profileName, "name", "")
						)
						if partner_name:
							clean_partner = partner_name.strip().rstrip(".")
							if not obj.name.strip().startswith(clean_partner):
								sender = clean_partner + ".\n"

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

	if not conf.get("notify administrators in messages"):
		lines = obj.name.split("\n")
		if len(lines) > 1:
			clean_line1 = lines[1].strip().lstrip(",").rstrip(".").strip().lower()
			if clean_line1 in _ADMIN_BADGES_LOWER:
				del lines[1]
				if len(lines) > 1 and not lines[1].lstrip().startswith("."):
					lines[1] = ". " + lines[1].lstrip()
				obj.name = "\n".join(lines)
		obj.name = _ADMIN_BADGES_PATTERN.sub("", obj.name)

	obj.name = sender + obj.name

	# Check if a message is selected
	if State.SELECTED in obj.states:
		obj.name = _("Selected") + ". " + obj.name

	return obj.name


def formatChatElementOnFocus(obj):
	"""Reorder or strip chat type prefix relative to chat name based on user config.

	Handles 'beforeName', 'afterName', and "don'tVoice" modes.
	"""
	if conf.get("voiceTypeAfterChatName") != "beforeName":
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
		question = ""
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
		elif text_blocks_before_type:
			question = text_blocks_before_type[-1]

		# Add total votes count if present
		votes_elem = next((c for c in children if getattr(c, "UIAAutomationId", "") == "Votes"), None)
		if votes_elem and votes_elem.name:
			votes_text = votes_elem.name.strip()
			if question and question in obj.name:
				obj.name = obj.name.replace(question, f"{question}, {votes_text}")
			elif type_name and type_name in obj.name:
				obj.name = obj.name.replace(type_name, f"{type_name}, {votes_text}")
			else:
				obj.name = f"{obj.name}, {votes_text}"
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
