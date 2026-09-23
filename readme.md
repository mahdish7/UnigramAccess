# UnigramAccess

* Author: Mahdi Sharifi <mahdii.sh7@gmail.com>
* Repository: [https://github.com/mahdish7/UnigramAccess](https://github.com/mahdish7/UnigramAccess)

UnigramAccess is an NVDA add-on that brings a comfortable, efficient, and fully accessible experience to Unigram (the Telegram client for Windows). It provides over 35 dedicated keyboard shortcuts, streamlines message and media navigation, adds convenient voice message and call controls, and eliminates unnecessary screen reader verbosity.

## Key Accessibility Features

* **Clean Navigation & Speech**: Eliminates cluttering phrases like "chats, tab, selected list" and "list". Announces "Not seen" before message text for unread messages and suppresses redundant "Seen" announcements.
* **Smart File & Media Details**: Announces file name and size on download/open buttons, and audio title and duration on playback buttons. Suppresses misleading static progress indicators when files are not downloading.
* **Enhanced Voice Messaging**: Distinct audio or text alerts for starting, sending, and canceling voice messages without shifting focus. Quick speech-to-text transcription, playback controls, and speed adjustment.
* **Call & Conference Controls**: Dedicated shortcuts to accept, decline, mute/unmute microphone, and toggle camera for both one-on-one calls and group voice chats.
* **Live Chat & Activity Monitoring**: Toggle automatic reading of incoming messages in the active chat (`ALT+L`) and track typing, online status, and member counts in real time (`ALT+T`).
* **Message Actions**: Quick reply, edit, forward, select, delete, and copy actions, along with a popup text viewer (`ALT+C`) for reading long messages comfortably.
* **Customizable Settings**: Independent configuration panel in NVDA settings (`NVDA+ALT+U`) for fine-tuning sender announcements, progress bars, recording indicators, link previews, and diagnostics.

## Keyboard Shortcuts

### Navigation & Layout
* **ALT+1**: Move focus to group topics list if open (or chats list, contacts list, or settings categories).
* **ALT+2**: Move focus to the last message, open profile, or settings details.
* **ALT+3**: Toggle focus between message edit field and previous position.
* **ALT+4**: Move focus to chat folders list.
* **ALT+5**: Move focus to open profile panel.
* **ALT+U**: Move focus to "unread messages" separator in the active chat.
* **ALT+shift+P**: Open current chat profile.
* **ALT+M**: Open main navigation menu.
* **ALT+end**: Scroll to the bottom of the chat.

### Messages & Interaction
* **ALT+T**: Announce chat name and status (member count, online status, typing). Double-press toggles real-time tracking of chat activity.
* **ALT+W**: Announce focused message timestamp and reactions. Double-press toggles automatic announcement of this information.
* **Left arrow**: Announce the original replied-to message. Double-press moves focus to it. In media albums, moves to previous media.
* **Right arrow**: Move to next media in a message with multiple media attachments.
* **ALT+C**: Show message text and speech-to-text recognized text in a popup text window.
* **control+C**: Copy message text (or focused link URL).
* **enter**: Reply to focused message.
* **backspace**: Edit focused message.
* **ALT+F**: Forward focused message.
* **control+space**: Switch focused message or chat to selection mode.
* **delete**: Delete focused message or chat.
* **shift+delete**: Delete focused message or chat for everyone / both sides.
* **ALT+shift+R**: Mark focused chat as read.
* **ALT+L**: Toggle automatic live announcement of incoming messages in the active chat.
* **control+ALT+C**: Open comments thread for the focused message.
* **ALT+Q**: Open Telegram Instant View for the current message.
* **control+shift+A**: Attach file or media to message.
* **control+N**: Start a new chat.
* **ALT+shift+L**: Copy live stream RTMP URL and stream key to clipboard (in broadcast window).
* **control+P**: Pin or unpin focused message or chat.
* **ALT+shift+O**: Open more options menu in the active chat.
* **Unassigned**: Save file attachment as...

### Media & Voice Messages
* **space**: Play or pause focused voice/video message, or open attached media in full-screen viewer.
* **ALT+P**: Play or pause currently active audio or voice message.
* **ALT+X**: Change media playback speed.
* **ALT+S**: Toggle focus between audio playback slider and previous position.
* **ALT+E**: Close active audio player bar.
* **control+R**: Start or stop recording a voice message.
* **control+D**: Cancel voice recording, message reply, or edit.
* **NVDA+ALT+R**: Convert voice message to text (transcribe speech-to-text).

### Calls
* **ALT+shift+C**: Start voice call or join group voice chat.
* **ALT+shift+V**: Start video call.
* **ALT+Y**: Accept incoming call (global shortcut).
* **ALT+N**: Decline incoming call, end active call, or leave voice chat (global shortcut).
* **ALT+A**: Mute or unmute microphone in active call or voice chat.
* **ALT+V**: Turn camera on or off in active video call.

### Search
* **ALT+I**: Open search results list in the active chat.
* **F3**: Go to next search result in the chat.
* **shift+F3**: Go to previous search result in the chat.

### Settings & Help
* **NVDA+ALT+U**: Open UnigramAccess settings panel.
* **ALT+H**: Show the complete list of UnigramAccess shortcuts in a popup window.

## Configuration Options

The UnigramAccess settings panel (accessible via **NVDA+ALT+U** or NVDA Settings -> UnigramAccess) is organized into 6 accessible categories:

### 1. General & Navigation
* **Interface language in Unigram**: Select the language used by Unigram to ensure accurate recognition of UI elements.
* **Chat type announcement in chats list**: Announce chat type before name, after name, or do not announce.

### 2. Messages & Reading
* **Announce sender name**: Control whether the sender's name is announced (disabled, sent messages only, received messages only, or all messages).
* **Up arrow action in empty message edit field**: Configure whether pressing Up Arrow in an empty edit field edits the last sent message, moves focus to the last message in the chat, or does nothing.
* **Speak "Not seen" before message text**: Announces unread status before the message text and suppresses "Seen".
* **Announce timestamp and reactions at end of messages**: Announce message sending or receiving time and reactions when moving through messages.
* **Announce "Administrator" and "Owner" badges in communities**: Speak admin badges on messages in communities.
* **Read descriptions of message links**: Read descriptions and summaries of web links and video previews attached to messages.
* **Clean up repetitive and boilerplate text in link previews**: Strip repetitive boilerplate text (such as generic YouTube platform descriptions) and tracking parameters from URLs.

### 3. Live Monitoring & Activity
* **Automatically read incoming messages in active chat**: Automatically announce incoming messages in the open chat in real time.
* **Announce chat activity**: Track and announce typing status, online status, and member count changes in real time.

### 4. Media & Voice Messages
* **Voice recording notification mode**: Choose between Sound notification, Text notification, or standard Telegram behavior.
* **Announce file details on media buttons**: Speak name, size, and duration on media action buttons.
* **Announce file download progress**: Announce download progress percentage when focused on active download buttons.

### 5. Deletion & Confirmation
* **Show confirmation dialog when deleting messages and chats**: Display a confirmation prompt before deleting.
* **Play sound when deleting messages and chats**: Play a sound confirmation when deleting messages or chats.

### 6. Logging & Diagnostics
* **Add-on log level**: Adjust add-on log level (Disabled, Error, Warning, Info, Debug) with buttons to open and clear the log file.

## Changes in version 1.0.0

* Initial official stable release of **UnigramAccess**.
* Complete modular architecture rewrite with clean separation of logic into dedicated modules (`unigram_ui`, `unigram_navigation`, `unigram_calls`, `unigram_messages`, `unigram_media`, `unigram_chats`, and `unigram_settings`).
* Full compatibility with NVDA 2025.1 through 2026.2+ and Python 3.12+.
* Over 35 dedicated accessibility hotkeys covering navigation, message handling, media playback, calls, and search.
* Advanced voice message controls: sound/text recording indicators, playback toggling, speed switching, slider focus, and speech-to-text recognition.
* Real-time live chat reading (`ALT+L`) and chat activity tracking (`ALT+T`).
* Global call controls (`ALT+Y` to answer, `ALT+N` to decline/hang up) and in-call mic/camera toggles.
* Popup text viewer (`ALT+C`) and instant in-chat shortcuts for reply, edit, forward, select, and delete.
* Dedicated configuration panel in NVDA settings with custom logging and diagnostic controls.
* Note: UnigramAccess is an independent, modernized continuation and fork of the legacy UnigramPlus add-on originally developed by Kostya Gladkiy.
