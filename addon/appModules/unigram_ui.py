# -*- coding:utf-8 -*-
from controlTypes import Role, State
import api
from .data import contacts_dialog_titles
from .unigram_logger import ulog as log


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


class UnigramUIHelper:
	def __init__(self, appModule):
		self.appModule = appModule

	def getMessagesElement(self):
		obj = self.appModule.saved_items.get("messages")
		if not obj or not obj.location or not obj.location.width:
			obj = next((item for item in self.getElements() if getattr(item, "UIAAutomationId", "") == "Messages"), None)
			if obj:
				self.appModule.saved_items.save("messages", obj)
		return obj

	def getChatsListElement(self):
		targetList = self.appModule.saved_items.get("chats")
		if targetList and targetList.location and targetList.location.width:
			log.debug("Found chats list in cache.")
			return targetList
		
		def get_version_tuple(v):
			try: return tuple(map(int, str(v).split(".")))
			except Exception: return (0, 0, 0, 0)
			
		log.debug(f"Chats list not in cache, detecting for version: {self.appModule.productVersion}")
		if get_version_tuple(self.appModule.productVersion) >= (11, 2, 13, 0):
			targetList = next((item for item in self.getElements() if item.role == Role.LIST and item.UIAAutomationId == "ChatsList"), False)
		else:
			targetList = next((item for item in reversed(self.getElements()) if item.role == Role.TABCONTROL and item.UIAAutomationId == "rpMasterTitlebar"), False)
			if not targetList:
				log.warning("Failed to find rpMasterTitlebar for older version of Unigram.")
				return False
			targetList = next((item for item in targetList.firstChild.children if item.role == Role.LIST and 	item.UIAAutomationId == "ChatsList"), False)
		if targetList:
			log.debug("Successfully found and cached chats list element.")
			self.appModule.saved_items.save("chats", targetList)
		else:
			log.warning("Chats list element could not be found.")
		return targetList

	def getMainContainer(self):
		container = self.appModule.saved_items.get("main_container")
		if container and getattr(container, "location", None) and container.location.width:
			return container

		fg = api.getForegroundObject()
		if not fg:
			return None
		if getattr(fg, "windowClassName", "") == "Windows.UI.Core.CoreWindow":
			self.appModule.saved_items.save("main_container", fg)
			return fg
		queue = list(getattr(fg, "children", []))
		while queue:
			item = queue.pop(0)
			if getattr(item, "windowClassName", "") == "Windows.UI.Core.CoreWindow":
				self.appModule.saved_items.save("main_container", item)
				return item
			if getattr(item, "role", None) == Role.PANE:
				queue.extend(getattr(item, "children", []))
		return None

	def getElements(self):
		try:
			container = self.getMainContainer()
			if container:
				return container.children
		except Exception:
			log.debugException("Error getting elements from main container")
		return []

	def get_first_item(self):
		try:
			container = self.getMainContainer()
			return getattr(container, "firstChild", None)
		except Exception:
			return None

	def get_settings_panel(self):
		settings_panel = next((item for item in self.getElements() if item.role in (Role.PANE, Role.LIST) and item.UIAAutomationId in ("ScrollingHost", "List", "") and ((item.previous and item.previous.UIAAutomationId == "DetailHeaderPresenter")  or item.location.width > 320)), None)
		if not settings_panel: return False
		return next(( item for item in settings_panel.children if State.FOCUSABLE in item.states), settings_panel.firstChild)

	def get_contacts_list(self):
		"""Find and return the contacts list or its first contact item in the contacts dialog."""
		try:
			curr = api.getFocusObject()
			dialog = None

			# Check if current focus is inside the Contacts dialog
			while curr:
				role = getattr(curr, "role", None)
				name = getattr(curr, "name", "") or ""
				if role == Role.DIALOG and name in contacts_dialog_titles.values():
					dialog = curr
					break
				curr = getattr(curr, "parent", None)

			# If focus is not inside the Contacts dialog, return immediately
			if not dialog:
				return False

			# Locate the ScrollingHost list inside the dialog
			contacts_list = None
			child = getattr(dialog, "firstChild", None)
			while child:
				c_role = getattr(child, "role", None)
				c_id = getattr(child, "UIAAutomationId", "")
				if c_role == Role.LIST and c_id == "ScrollingHost":
					contacts_list = child
					break
				child = getattr(child, "next", None)

			if not contacts_list:
				return False

			# Find the first contact item (Role.LISTITEM), skipping header action buttons
			item = getattr(contacts_list, "firstChild", None)
			while item:
				if getattr(item, "role", None) == Role.LISTITEM:
					return item
				item = getattr(item, "next", None)

			return contacts_list
		except Exception:
			log.debugException("Error getting contacts list")
			return False

	def get_settings_list(self):
		a = next((item for item in self.getElements() if item.role == Role.PANE and item.UIAAutomationId == "ScrollingHost" and item.firstChild.next.UIAAutomationId == "Title" and item.firstChild.next.next.UIAAutomationId == "Identity"), None)
		if not a:
			return False
		try: b = a.firstChild.next.next.next.next.firstChild
		except Exception: b = False
		if b: return b
		else: return False

	def is_message_object(self, obj):
		try:
			if not obj: return False
			if getattr(obj, "UIAAutomationId", "") == "Message_item": return True
			parent = getattr(obj, "parent", None)
			if parent and getattr(parent, "UIAAutomationId", "") == "Messages": return True
			return False
		except Exception: return False

	def get_branch_list(self):
		branch_list = next((item for item in self.getElements() if item.role == Role.LIST and item.UIAAutomationId == "TopicList"), False)
		if branch_list: return branch_list
		else: return False

	def get_profile_panel(self):
		list = self.appModule.profilePanelElement
		if not list or not list.location.width:
			list = next((item for item in self.getElements() if (item.role == Role.LIST and item.UIAAutomationId == "ScrollingHost" and item.firstChild and item.firstChild.UIAAutomationId in ("Photo", "Segments")) or (item.role == Role.LINK and item.UIAAutomationId == "Photo" and item.next.UIAAutomationId == "Title")), None)
		if not list:
			return False
		if list.UIAAutomationId == "Photo":
			# If the profile does not contain any tabs, then the focus is set to the profile photo
			return list
		self.appModule.profilePanelElement = list
		list2 = list.firstChild
		for i in range(15):
			if list2.role == Role.LIST:
				# Now we find the selected element to set focus on it
				return next((item for item in list2.children if State.SELECTED in item.states), list2.firstChild)
			else: list2 = list2.next
		return list.firstChild
