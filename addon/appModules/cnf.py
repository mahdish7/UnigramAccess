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
	"voiceFolderNames = boolean(default=True)",
	"voiceMessageRecordingIndicator = string(default=audio)",
	"voicingPerformanceIndicators = string(default=none)",
	"audioPlaybackWhenDeleted = boolean(default=False)",
	"confirmation_at_deletion = boolean(default=False)",
	"actionDescriptionForLinks = boolean(default=True)",
	"voiceFullDescriptionOfLinkToYoutube = boolean(default=True)",
	"voiceMediaButtonDetails = boolean(default=True)",
	"isAnnouncesAnswers = boolean(default=True)",
	"isFixedToggleButton = boolean(default=False)",
	"saySenderName = string(default=none)",
	"voice_the_presence_of_a_reaction = boolean(default=True)",
	"report premium accounts = boolean(default=True)",
	"automatically announce new messages = boolean(default=False)",
	"automatically announce activity in chats = boolean(default=False)",
	"notify administrators in messages = boolean(default=True)",
	"action_when_pressing_up_arrow_in_text_field = string(default=normal)",
	"announce_end_of_message = boolean(default=True)",
	"custom_log_level = string(default=disabled)"
)

class cnf:
	def __init__(self):
		self.path = os.path.join(globalVars.appArgs.configPath, "UnigramAccess.ini")
		self.conf = ConfigObj(self.path, configspec=spec )
		validator = Validator()
		self.conf.validate(validator, copy=True)
		self.conf.write()
	def get(self, key):
		return self.conf[key]
	def set(self, key, value):
		self.conf[key] = value
		self.conf.write()

try: conf = cnf()
except Exception:
	path = os.path.join(globalVars.appArgs.configPath, "UnigramAccess.ini")
	os.remove(path)
	conf = cnf()