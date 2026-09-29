from  configobj  import  ConfigObj
from configobj.validate import Validator
import os
import globalVars
import languageHandler
import addonHandler
addonHandler.initTranslation()

_user_lang = languageHandler.getLanguage().replace("_", "-").lower()
if _user_lang in ("pt-br", "pt"):
	lang = "pt-br"
elif _user_lang.startswith("zh-cn") or _user_lang.startswith("zh-sg"):
	lang = "zh-hans"
elif _user_lang.startswith("zh"):
	lang = "zh-hant"
elif _user_lang in ("sk", "sl"):
	lang = "sk"
else:
	lang = _user_lang.split("-")[0]

listLanguages = {
	"ar": _("Arabic"),
	"be": _("Belarusian"),
	"ca": _("Catalan"),
	"cs": _("Czech"),
	"de": _("German"),
	"en": _("English"),
	"es": _("Spanish"),
	"fa": _("Persian"),
	"fi": _("Finnish"),
	"fr": _("French"),
	"he": _("Hebrew"),
	"hr": _("Croatian"),
	"hu": _("Hungarian"),
	"id": _("Indonesian"),
	"it": _("Italian"),
	"kk": _("Kazakh"),
	"ko": _("Korean"),
	"ms": _("Malay"),
	"nb": _("Norwegian"),
	"nl": _("Dutch"),
	"pl": _("Polish"),
	"pt-br": _("Portuguese (Brazil)"),
	"ro": _("Romanian"),
	"ru": _("Russian"),
	"sk": _("Slovak"),
	"sr": _("Serbian"),
	"sv": _("Swedish"),
	"tr": _("Turkish"),
	"uk": _("Ukrainian"),
	"uz": _("Uzbek"),
	"zh-hans": _("Chinese (Simplified)"),
	"zh-hant": _("Chinese (Traditional)"),
}



spec = (
	f"lang = string(default={lang if lang in listLanguages else 'en'})",
	"voiceTypeAfterChatName = string(default=beforeName)",
	"unreadBeforeMessageContent = boolean(default=True)",
	"voiceMessageRecordingIndicator = string(default=audio)",
	"voiceDownloadProgress = boolean(default=True)",
	"audioPlaybackWhenDeleted = boolean(default=True)",
	"skip_deletion_confirmation = boolean(default=False)",
	"actionDescriptionForLinks = boolean(default=True)",
	"cleanLinkDescriptions = boolean(default=True)",
	"voiceMediaButtonDetails = boolean(default=True)",
	"saySenderName = string(default=none)",
	"automatically announce new messages = boolean(default=False)",
	"automatically announce activity in chats = boolean(default=False)",
	"suppress_admin_badges = boolean(default=False)",
	"suppress_nickname_in_messages = boolean(default=False)",
	"action_when_pressing_up_arrow_in_text_field = string(default=edit)",
	"suppress_end_of_message = boolean(default=False)",
	"suppressProgressBarUpdates = boolean(default=True)",
	"custom_log_level = string(default=disabled)"
)

class cnf:
	def __init__(self):
		self.path = os.path.join(globalVars.appArgs.configPath, "UnigramAccess.ini")
		self.conf = ConfigObj(self.path, configspec=spec )
		# Migrate legacy config keys if present
		if "notify administrators in messages" in self.conf:
			try:
				if not self.conf.as_bool("notify administrators in messages"):
					self.conf["suppress_admin_badges"] = True
			except Exception:
				pass
			del self.conf["notify administrators in messages"]
		if "announce_nickname_in_messages" in self.conf:
			try:
				if not self.conf.as_bool("announce_nickname_in_messages"):
					self.conf["suppress_nickname_in_messages"] = True
			except Exception:
				pass
			del self.conf["announce_nickname_in_messages"]
		if "announce_end_of_message" in self.conf:
			try:
				if not self.conf.as_bool("announce_end_of_message"):
					self.conf["suppress_end_of_message"] = True
			except Exception:
				pass
			del self.conf["announce_end_of_message"]
		if "confirmation_at_deletion" in self.conf:
			del self.conf["confirmation_at_deletion"]
		validator = Validator()
		self.conf.validate(validator, copy=True)
		self.conf.write()
	def get(self, key, default=None):
		try:
			return self.conf[key]
		except KeyError:
			return default
	def set(self, key, value):
		self.conf[key] = value
		self.conf.write()

try: conf = cnf()
except Exception:
	path = os.path.join(globalVars.appArgs.configPath, "UnigramAccess.ini")
	os.remove(path)
	conf = cnf()