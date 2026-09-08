# -*- coding:utf-8 -*-
from controlTypes import Role, State
import api
from .unigram_logger import ulog as log


class UnigramSettings:
	"""Manages settings screen detection, category navigation, and detail panel interactions."""

	def __init__(self, appModule):
		self.appModule = appModule

	def get_navigation_list(self):
		"""Locate and return the settings Navigation list control (Role.LIST)."""
		try:
			elements = self.appModule.ui_helper.getElements()
			for item in elements:
				if getattr(item, "role", None) == Role.LIST and getattr(item, "UIAAutomationId", "") == "Navigation":
					return item
				if getattr(item, "role", None) == Role.PANE and getattr(item, "UIAAutomationId", "") == "ScrollingHost":
					nav = next(
						(
							child for child in getattr(item, "children", [])
							if getattr(child, "role", None) == Role.LIST and getattr(child, "UIAAutomationId", "") == "Navigation"
						),
						None
					)
					if nav:
						return nav
			return None
		except Exception:
			log.debugException("Error getting settings navigation list")
			return None

	def get_detail_panel(self):
		"""Locate and return the settings right-side detail panel or its first focusable control."""
		try:
			elements = self.appModule.ui_helper.getElements()
			settings_panel = next(
				(
					item for item in elements
					if item.role in (Role.PANE, Role.LIST)
					and item.UIAAutomationId in ("ScrollingHost", "List", "")
					and ((item.previous and item.previous.UIAAutomationId == "DetailHeaderPresenter") or (item.location and item.location.width > 320))
				),
				None
			)
			if not settings_panel:
				return None
			return next(
				(child for child in getattr(settings_panel, "children", []) if State.FOCUSABLE in getattr(child, "states", set())),
				getattr(settings_panel, "firstChild", None)
			)
		except Exception:
			log.debugException("Error getting settings detail panel")
			return None

	def is_in_settings(self):
		"""Check whether Unigram is currently displaying the settings screen."""
		try:
			# Fast check: If the currently focused element is inside Navigation
			focus_obj = api.getFocusObject()
			if focus_obj:
				parent = getattr(focus_obj, "parent", None)
				if getattr(focus_obj, "UIAAutomationId", "") == "Navigation" or (parent and getattr(parent, "UIAAutomationId", "") == "Navigation"):
					return True

			# Structural check: If Navigation list exists and is visible on screen
			nav = self.get_navigation_list()
			if nav and getattr(nav, "location", None) and nav.location.width > 0:
				return True

			return False
		except Exception:
			return False

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

	def to_detail_panel(self):
		"""Move keyboard focus to the settings right-side detail panel."""
		try:
			panel_control = self.get_detail_panel()
			if panel_control:
				panel_control.setFocus()
				return True
			return False
		except Exception:
			log.debugException("Error focusing settings detail panel")
			return False
