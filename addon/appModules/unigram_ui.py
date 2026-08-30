# -*- coding:utf-8 -*-
from controlTypes import Role, State
import api
from .unigram_logger import ulog as log

class UnigramUIHelper:
	def __init__(self, appModule):
		self.appModule = appModule

	def getMessagesElement(self):
		obj = self.appModule.saved_items.get("messages")
		if not obj or not obj.location or not obj.location.width:
			# obj = next((item for item in self.getElements() if item.UIAAutomationId == "Messages"), False)
			obj = None
			item = self.get_first_item()
			while item:
				if item.UIAAutomationId == "Messages":
					obj = item
					item = None
				else: item = item.next
			if obj: self.appModule.saved_items.save("messages", obj)
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

	def getElements(self):
		try: return api.getForegroundObject().lastChild.previous.children
		except Exception: return []
	
	def get_first_item(self):
		try: return api.getForegroundObject().lastChild.previous.firstChild
		except Exception: return []

	def get_settings_panel(self):
		settings_panel = next((item for item in self.getElements() if item.role in (Role.PANE, Role.LIST) and item.UIAAutomationId in ("ScrollingHost", "List", "") and ((item.previous and item.previous.UIAAutomationId == "DetailHeaderPresenter")  or item.location.width > 320)), None)
		if not settings_panel: return False
		return next(( item for item in settings_panel.children if State.FOCUSABLE in item.states), settings_panel.firstChild)

	def get_contacts_list(self):
		try:
			dialog = next((item for item in self.getElements() if item.role == Role.DIALOG and item.firstChild.next.UIAAutomationId == "SearchField" and item.firstChild.next.next.role == Role.LIST and item.firstChild.next.next.UIAAutomationId == "ScrollingHost"), None)
			if not dialog: return False
			first_item = next((item for item in dialog.children if item.role == Role.LISTITEM), None)
			return first_item
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
			if obj.UIAAutomationId == "Message_item": return True
			else: return False
		except Exception: return False

	def get_branch_list(self):
		branch_list = next((item for item in self.getElements() if item.role == Role.LIST and item.UIAAutomationId == "TopicList"), False)
		if branch_list: return branch_list
		else: return False

	def get_profile_panel(self):
		list = self.appModule.profile_panel_element
		if not list or not list.location.width:
			list = next((item for item in self.getElements() if (item.role == Role.LIST and item.UIAAutomationId == "ScrollingHost" and item.firstChild and item.firstChild.UIAAutomationId in ("Photo", "Segments")) or (item.role == Role.LINK and item.UIAAutomationId == "Photo" and item.next.UIAAutomationId == "Title")), None)
		if not list:
			return False
		if list.UIAAutomationId == "Photo":
			# If the profile does not contain any tabs, then the focus is set to the profile photo
			return list
		self.appModule.profile_panel_element = list
		list2 = list.firstChild
		for i in range(15):
			if list2.role == Role.LIST:
				# Now we find the selected element to set focus on it
				return next((item for item in list2.children if State.SELECTED in item.states), list2.firstChild)
			else: list2 = list2.next
		return list.firstChild
