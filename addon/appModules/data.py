# -*- coding:utf-8 -*-
# UnigramAccess: Static data, localization dictionaries, and UI label mappings.
#
# Note: When adding new language entries to any dictionary, please keep the
# language codes sorted alphabetically (e.g., 'ar', 'de', 'en', 'fa', 'ru', ...).

# ============================================================================
# 1. MESSAGE HISTORY & FORMATTING
# ============================================================================

# Keywords for parsing message elements in the chat history (read status, time, and sender).
# Format per language code:
#   "lang_code": (
#       [0] read status phrase (e.g. ". Seen"),
#       [1] unread status phrase (e.g. ". Not seen"),
#       [2] sent message prefix / timestamp separator (e.g. ", Sent at "),
#       [3] received message prefix / timestamp separator (e.g. ", Received at "),
#       [4] leading phrase before sent message text (usually identical to [2]),
#       [5] leading phrase before received message text (usually identical to [3]),
#   )
keywordsInMessages = {
	"ar": (". تم قرائتها", ". غير مقروءة", ", تم الإرسال ⁨الساعة ⁨", ", تم التسليم ⁨الساعة ⁨", ", تم الإرسال ⁨الساعة ⁨", ", تم التسليم ⁨الساعة ⁨"),
	"be": (". Прагледжана", ". Не прагледжана", ", Адпраўлена а ", ", Атрымана а ", ", Адпраўлена а ", ", Атрымана а "),
	"cs": (". Viděno", ". Neviděno", ", Odesláno v ", ", Přijato v ", ", Odesláno v ", ", Přijato v "),
	"de": (". Gesehen", ". Noch nicht gesehen", ", Gesendet um ", ", Empfangen um ", ", Gesendet um ", ", Empfangen um "),
	"en": (". Seen", ". Not seen", ", Sent at ", ", Received at ", ", Sent at ", ", Received at "),
	"es": (". Visto", ". No visto", ", Enviado a las ", ", Recibido el a las ", ", Enviado a las ", ", Recibido el a las "),
	"fa": (". دیده شده", ". دیده نشده", ", ⁨در ⁨", ", ⁨در ⁨", ", ⁨در ⁨", ", ⁨در ⁨"),
	"fi": (". Nähty", ". Ei nähty", ", Lähetetty klo ", ", Vastaanotettu klo ", ", Lähetetty klo ", ", Vastaanotettu klo "),
	"fr": (". Vu", ". Non vu", ", Envoyé à ", ", Reçu à ", ", Envoyé à ", ", Reçu à "),
	"hr": (". Viđeno", ". Nije viđeno", ", Poslano u ", ", Primljeno u ", ", Poslano u ", ", Primljeno u "),
	"it": (". Visto", ". Non visto", ", Inviato alle ", ", Ricevuto alle ", ", Inviato alle ", ", Ricevuto alle "),
	"nb": (". Sett", ". Ikke sett", ", Sendt ", ", Mottatt ", ", Sendt ", ", Mottatt "),
	"pl": (". Wyświetlono", ". Nie wyświetlono", ", Wysłana o ", ", Odebrane o ", ", Wysłana o ", ", Odebrane o "),
	"pt": (". Visto", ". Não visto", ", Enviado às ", ", Recebido às ", ", Enviado às ", ", Recebido às "),
	"ro": (". Citit", ". Necitit.", ", Trimis la ", ", Primit la ", ", Trimis la ", ", Primit la "),
	"ru": (". Прочитано", ". Не прочитано", ", Отправлено в ", ", Получено в ", ", Отправлено в ", ", Получено в "),
	"sl": (". Videné", ". Nevidené", ", Odoslať o ", ", Prijaté o ", ", Odoslať o ", ", Prijaté o "),
	"sr": (". Viđeno", ". Nije viđeno", ", Poslato u ", ", Primljeno u ", ", Poslato u ", ", Primljeno u "),
	"tr": (". Görüldü", ". Görülmedi", "tarihinde gönderildi.", "tarihinde alındı.", ", bugün ", ", bugün "),
	"uk": (". Прочитане", ". Непрочитане", ", Надіслано ", ", Отримано ", ", Надіслано ", ", Отримано "),
	"zh": (". 已讀", ". 未讀", ", 傳了  今天", ", 收到了  今天", ", 傳了  今天", ", 收到了  今天"),
}

# Administrator and owner rank badges in community messages.
# Format: "lang_code": ("AdminTitle", "OwnerTitle")
phrase_administrator_in_message = {
	"ar": ("مشرف", "المالك"),
	"cs": ("Správce", "Vlastník"),
	"en": ("Admin", "Owner"),
	"es": ("Administrador", "Propietario"),
	"fr": ("Administrateur", "Propriétaire"),
	"hr": ("Administrator", "Vlasnik"),
	"it": ("Proprietario", "Amministratore"),
	"ne": ("मालिक", "प्रसाशक"),
	"ru": ("Администратор", "Владелец"),
	"sr": ("Administrator", "Vlasnik"),
	"uk": ("Адміністратор", "Власник"),
	"zh": ("管理員", "擁有者"),
}

# Separator text for unread messages divider in chat history.
# Format: "lang_code": ("keyword", ...)
unread_messages_keywords = {
	"en": ("unread messages",),
}


# ============================================================================
# 2. COMPOSER HEADER & INPUT FIELD
# ============================================================================

# Action type for the cancel button above the message input field (reply vs edit).
# Format: "action": {"lang_code": ("keyword", ...)}
composer_header_cancel_types = {
	"reply": {
		"en": ("reply",),
	},
	"edit": {
		"en": ("editing", "edit"),
	},
}

# Spoken replacement titles for composer headers to improve speech clarity.
# Format: "original_title": _("replacement_title")
composer_header_title_replacements = {
	"Edit": _("Editing"),
}


# ============================================================================
# 3. CHATS & DIALOGS
# ============================================================================

# Keywords for identifying chat entity type (channel, group, bot) in deletion/leave dialogs.
# Format: "entity_type": {"lang_code": ("keyword", ...)}
chat_deletion_keywords = {
	"channel": {
		"en": ("channel",),
	},
	"group": {
		"en": ("group",),
	},
	"bot": {
		"en": ("bot",),
	},
}

# Window title of the Contacts dialog.
# Format: "lang_code": "title"
contacts_dialog_titles = {
	"en": "Contacts",
}


# ============================================================================
# 4. CONTEXT MENU & ACTIONS
# ============================================================================

# Option labels in the right-click context menu of messages and chats.
# Format: "action": {"lang_code": ("keyword", ...)}
context_menu_items = {
	"select": {
		"en": ("select",),
	},
	"delete": {
		"en": ("delete",),
	},
	"forward": {
		"en": ("forward",),
	},
	"reply": {
		"en": ("reply",),
	},
	"edit": {
		"en": ("edit",),
	},
	"save_as": {
		"en": ("save as",),
	},
	"pin": {
		"en": ("pin", "unpin"),
	},
	"read": {
		"en": ("mark as read", "mark as unread"),
	},
}

# Legacy font icon glyphs for context menu options (for backwards compatibility).
# Format: "action": "unicode_char"
icons_from_context_menu = {
	"attach": "",
	"unpin": "",
	"reply": "",
	"copy": "",
	"edit": "",
	"forward": "",
	"delete": "",
	"save_as": "",
	"select": "",
	"read": "",
	"unread": "",
}


# ============================================================================
# 5. BUTTONS, ICONS & MEDIA
# ============================================================================

# Spoken labels for buttons with technical IDs or missing names.
# Format: "technical_id": _("spoken_label")
labels_for_buttons = {
	"Back": _("Back"),
	"Menu": _("Menu"),
	"Pin": _("Attach"),
	"Edit": _("Edit"),
	"Photo": _("Photo"),
	"Image": _("Image"),
	"InviteLink": _("Invite link"),
	"FieldSeconds": _("Choose time"),
	"TitleField": _("Title field"),
}

# Spoken labels for icon-only buttons without text names.
# Format: "unicode_icon": _("spoken_label")
labels_in_buttons = {
	"": _("Go to next reaction"),
	"": _("Insert emojis"),
	"": _("Done"),
	"": _("Next"),
	"": _("Merge files"),
	"": _("Search"),
	"": _("Delete"),
	"": _("Close"),
}

# Keywords indicating active download/upload transfer state in media buttons.
# Format: "lang_code": ("keyword", ...)
active_download_keywords = {
	"en": ("cancel",),
}
