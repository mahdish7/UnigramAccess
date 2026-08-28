# -*- coding: utf-8 -*-
# Update checking and downloading logic for UnigramAccess addon

import os
import urllib.request
import wx
import gui
import core
import globalVars
import addonHandler
addonHandler.initTranslation()

from appModules.cnf import lang

path_to_server = ""

def no_updates_dialog():
	from gui.message import MessageDialog
	MessageDialog(
		gui.mainFrame,
		message=_("No updates available"),
		title=_("UnigramAccess update"),
	).addOkButton().Show()

def onCheckForUpdates(event = False, is_start = False):
	if not path_to_server:
		if not is_start: wx.CallAfter(no_updates_dialog)
		return
	import versionInfo
	NVDAVersion = (versionInfo.version_year, versionInfo.version_major, versionInfo.version_minor)
	fp = os.path.join(globalVars.appArgs.configPath, "unigramaccess.nvda-addon")
	addon_version_str = addonHandler.getCodeAddon().manifest["version"]
	addon_version = tuple(int(x) for x in addon_version_str.split("."))
	try: response = urllib.request.urlopen(path_to_server+"version.txt", timeout=3).read().decode('utf-8')
	except Exception:
		if not is_start: wx.CallAfter(no_updates_dialog)
		return
	response = str(response)
	str_last_version = response.split("\n")[0]
	last_version = tuple(int(x) for x in str_last_version.split("."))
	minimum_version_str = response.split("\n")[1]
	minimum_version = tuple(int(x) for x in minimum_version_str.split("."))
	url = response.split("\n")[-1]
	if last_version > addon_version and NVDAVersion >= minimum_version:
		wx.CallAfter(window_for_update, None, str_last_version, url)
	elif not is_start: wx.CallAfter(no_updates_dialog)

class window_for_update(wx.Frame):
	def __init__(self, parent, str_last_version, url):
		title = _("UnigramAccess update")
		text = _("A new version of the add-on is available. Do you want to update UnigramAccess to version %version?").replace("%version", str_last_version)
		no_resize = wx.DEFAULT_FRAME_STYLE & ~ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)
		super().__init__(parent, title=title, size=(640, 360), style=no_resize)
		self.url = str(url)
		self.str_last_version = str_last_version
		self.Centre()
		panel = wx.Panel(self, wx.ID_ANY)
		self.text = wx.TextCtrl(panel, -1, text, style = wx.TE_MULTILINE | wx.TE_READONLY)
		self.text.SetValue(text)
		self.text.SetFocus()
		self.button_ok = wx.Button(panel, label=_("Yes, update"), id=-1)
		self.button_close= wx.Button(panel, label=_("No, not now"), id=-1)
		self.button_ok.Bind(wx.EVT_BUTTON,self.download_update)
		self.button_close.Bind(wx.EVT_BUTTON,self.window_close)
		sizer = wx.BoxSizer(wx.VERTICAL)
		buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
		buttons_sizer.Add(self.button_ok)
		buttons_sizer.Add(self.button_close)
		sizer.Add(self.text, 1, wx.EXPAND)
		sizer.Add(buttons_sizer, flag = wx.ALL | wx.ALIGN_RIGHT, border=5)
		panel.SetSizer(sizer)
		self.Raise()
		self.Show(True)
		self.get_documentation()

	def download_update(self, event):
		self.text.SetValue(_("Download in progress"))
		self.text.SetFocus()
		self.button_ok.Disable()
		self.button_close.Disable()
		try: response_addon = urllib.request.urlopen(self.url).read()
		except Exception:
			no_updates_dialog()
			self.Close()
			return
		fp = os.path.join(globalVars.appArgs.configPath, "unigramaccess.nvda-addon")
		with open(fp, 'wb') as addon:
			addon.write(response_addon)
		self.setup_update(fp)

	def window_close(self, event):
		self.Close()
	
	def get_documentation(self):
		if not path_to_server:
			self.text.SetValue(self.text.GetValue() + "\n" + _("No update information"))
			return
		doc = False
		url = path_to_server+"documentation/"+self.str_last_version+"/"+lang+".txt"
		try: doc = urllib.request.urlopen(url).read().decode('utf-8')
		except Exception: pass
		try:
			url = path_to_server+"documentation/"+self.str_last_version+"/en.txt"
			if not doc: doc = urllib.request.urlopen(url).read().decode('utf-8')
		except Exception: pass
		if doc: text = "\n"+_("Changes in this version:")+"\n"+str(doc)
		else: text = "\n"+_("No update information")
		self.text.SetValue(self.text.GetValue()+text)

	def setup_update(self, fp):
		curAddons = addonHandler.getAvailableAddons()
		bundle = addonHandler.AddonBundle(fp)
		bundleName = bundle.manifest['name']
		prevAddon = next((addon for addon in curAddons if not addon.isPendingRemove and bundleName == addon.manifest['name']), None)
		if prevAddon: prevAddon.requestRemove()
		addonHandler.installAddonBundle(bundle)
		core.restart()
