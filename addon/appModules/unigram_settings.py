# -*- coding:utf-8 -*-
from controlTypes import Role, State
import api
from ui import message
from .unigram_logger import ulog as log


class UnigramSettings:
	"""Manages settings screen detection, category navigation, and detail/content panel interactions."""

	def __init__(self, appModule):
		self.appModule = appModule

	def get_navigation_list(self):
		"""Locate and return the settings Navigation category list control (Role.LIST)."""
		try:
			ui_helper = getattr(self.appModule, "ui_helper", None)
			elements = ui_helper.getElements() if ui_helper else []
			for item in elements:
				if getattr(item, "role", None) == Role.LIST and getattr(item, "UIAAutomationId", "") == "Navigation":
					return item
				if getattr(item, "role", None) == Role.PANE and getattr(item, "UIAAutomationId", "") == "ScrollingHost":
					for child in getattr(item, "children", []):
						if getattr(child, "role", None) == Role.LIST and getattr(child, "UIAAutomationId", "") == "Navigation":
							return child
			return None
		except Exception:
			log.debugException("Error getting settings navigation list")
			return None

	def to_categories_list(self):
		"""Move keyboard focus to the settings category list (selected item or first item)."""
		try:
			nav = self.get_navigation_list()
			if not nav:
				return False

			children = getattr(nav, "children", [])
			# Priority 1: Currently selected category
			selected = next(
				(c for c in children if getattr(c, "role", None) == Role.LISTITEM and State.SELECTED in getattr(c, "states", set())),
				None
			)
			if selected:
				selected.setFocus()
				return True

			# Priority 2: First category item
			first = next(
				(c for c in children if getattr(c, "role", None) == Role.LISTITEM),
				getattr(nav, "firstChild", None)
			)
			if first:
				first.setFocus()
				return True

			nav.setFocus()
			return True
		except Exception:
			log.debugException("Error focusing settings categories list")
			return False

	def _find_focus_target(self, panel):
		"""Find the first focusable control within a detail panel from top to bottom."""
		children = getattr(panel, "children", [])
		if not children:
			first = getattr(panel, "firstChild", None)
			return first if first and (getattr(first, "isFocusable", False) or State.FOCUSABLE in getattr(first, "states", set())) else panel

		for child in children:
			child_states = getattr(child, "states", set())
			if getattr(child, "isFocusable", False) or State.FOCUSABLE in child_states:
				return child
			for sub in getattr(child, "children", []):
				sub_states = getattr(sub, "states", set())
				if getattr(sub, "isFocusable", False) or State.FOCUSABLE in sub_states:
					return sub

		first = getattr(panel, "firstChild", None)
		return first if first else panel

	def get_detail_panel(self):
		"""Locate and return the active detail/content panel focusable control."""
		try:
			ui_helper = getattr(self.appModule, "ui_helper", None)
			if not ui_helper:
				return None

			# If chat messages are present, yield to chat message handling
			if ui_helper.getMessagesElement():
				return None

			nav = self.get_navigation_list()
			elements = ui_helper.getElements()

			for item in elements:
				if item == nav:
					continue
				if getattr(item, "role", None) not in (Role.LIST, Role.PANE):
					continue

				uia_id = getattr(item, "UIAAutomationId", "")
				# Must be a ScrollingHost or List container
				if uia_id not in ("ScrollingHost", "List"):
					continue

				# Exclude left-pane navigation and specialized containers
				if uia_id in ("ChatsList", "TopicList", "ChatFolders", "Navigation"):
					continue
				if ui_helper._is_profile_host(item) or ui_helper._is_topic_host(item) or ui_helper.is_stories_list(item):
					continue

				# Must contain focusable interactive children
				target = self._find_focus_target(item)
				if target and target != item:
					return target

			return None
		except Exception:
			log.debugException("Error getting settings detail panel")
			return None

	def is_in_settings(self):
		"""Check whether Unigram is currently displaying the settings screen or a settings subpage."""
		try:
			ui_helper = getattr(self.appModule, "ui_helper", None)
			if ui_helper and ui_helper.getMessagesElement():
				return False

			if self.get_navigation_list():
				return True

			if self.get_detail_panel() is not None:
				return True

			return False
		except Exception as e:
			log.debugException(f"is_in_settings error: {e}")
			return False

	def to_detail_panel(self):
		"""Move keyboard focus to the settings right-side detail panel or subpage content."""
		try:
			panel_control = self.get_detail_panel()
			if panel_control:
				current_focus = api.getFocusObject()
				if current_focus == panel_control:
					name = getattr(panel_control, "name", "")
					if name:
						message(name)
					return True
				try:
					panel_control.setFocus()
				except Exception:
					parent = getattr(panel_control, "parent", None)
					if parent:
						parent.setFocus()
					else:
						raise
				return True
			return False
		except Exception:
			log.debugException("Error focusing settings detail panel")
			return False
