# UnigramAccess

* Author: Mahdi Sharifi <mahdii.sh7@gmail.com>
* Repository: [https://github.com/mahdish7/UnigramAccess](https://github.com/mahdish7/UnigramAccess)


Use Unigram in a more comfortable and productive way. This addon provides many hotkeys for a quick and comfortable use of Unigram and makes a lot of small improvements.
## Some of the major improvements are:

* Adds a significant improvement to the display of messages such as a poll, a link, or a message with attached media.
* When focus enters the list of chats, it removes such phrases as: "chats, tab, selected list". And when the focus hits the list of messages, the phrase "list".
* The name and size of the file will be spoken when the cursor is focused on the "Open File" button or the "Download File" button, and when the cursor is focused on the play button of the audio file, you will hear its name and duration.
* When focus is placed on a voice message that is currently being played, first information about the time of its playback is announced, and then all other information.
* When the focus is on a message that contains information about a call, the duration of this call is announced.
* When focusing on a selected message in a chat, you will first hear the information that it is selected, and then the content of the message.
* Now, when moving in the chat, the phrase "Seen" will not be pronounced at all, and the phrase "Not seen" will be pronounced before the content of the message. This feature currently only works in English, Russian, Ukrainian, Spanish, Portuguese, Polish, Croatian, Turkish, and Persian.
* Significantly improved the function of recording voice messages. Recording, sending and canceling the recording of a voice message are accompanied by characteristic sounds. Also, when performing these functions, the focus remains in its position and does not jump to either the record button or the message input field.
* If the media attached to the message is opened using the spacebar, then after closing it, the focus will return to the last element that was in focus.
* The add-on allows you to completely disable the announcement of progress bars, as well as disable only the announcement of the progress bar for playing voice messages.

## Hotkey List:

### Navigation & Layout
* **ALT+1**: Move focus to chat list.
* **ALT+2**: Move focus to the last message in an open chat.
* **ALT+3**: Move focus to "unread messages" label.
* **ALT+4**: Move focus to list of chat folders.
* **ALT+5**: Move focus to open profile.
* **ALT+6**: Move focus to the list of group threads.
* **ALT+shift+P**: Open current chat profile.
* **ALT+M**: Open navigation menu.

### Messages & Interaction
* **ALT+D**: Move the focus to the edit field (pressing it again returns focus to the previous location).
* **ALT+T**: Announce the name and status of an open chat.
* **ALT+W**: Announce the time a message was sent or received and its reactions. Double-clicking toggles the announcement mode.
* **NVDA+control+1-9, 0**: Read the N-th most recent message in the chat without moving system focus (1 is the newest, 0 is the 10th). Also moves the NVDA navigator object.
* **Left arrow**: Announce the original message that was replied to. Double-pressing moves focus to it.
* **ALT+C**: Show message text in a popup window.
* **control+C**: Copy the message text (or link if focused on a link).
* **ALT+shift+L**: Copy data for broadcasting to the clipboard.
* **delete**: Delete a message or chat.
* **shift+delete**: Delete message or chat from both sides.
* **enter**: Reply to message.
* **backspace**: Edit message.
* **ALT+F**: Forward message.
* **control+space**: Switch to selection mode.
* **ALT+shift+R**: Mark a chat as read.
* **ALT+L**: Enable automatic reading of new messages in the current chat.
* **control+ALT+C**: Open comments.
* **Unassigned**: Pin a message or chat.
* **control+shift+A**: Press "Attach file" button.
* **control+N**: Press "New chat" button.
* **ALT+Q**: Press "Instant view" button if included in the current message.

### Media & Voice Messages
* **space**: Play/stop the focused voice or video message, or open a media file attached to the current message.
* **ALT+P**: Play/pause the voice message currently playing.
* **ALT+S**: Increase/decrease the playback speed of voice messages.
* **ALT+E**: Close audio player.
* **control+R**: Start/stop voice message recording.
* **control+D**: Once: cancel voice message recording. Twice: change the notification type for voice messages.
* **control+ALT+rightArrow**: Fast forward a voice message.
* **control+ALT+leftArrow**: Rewind a voice message.
* **NVDA+ALT+R**: Convert voice message to text.

### Calls
* **ALT+shift+C**: Call if it's a contact, or enter a voice chat if it's a group.
* **ALT+shift+V**: Press the video call button.
* **ALT+Y**: Accept call.
* **ALT+N**: Decline an incoming call, end an active call, or leave a voice chat.
* **ALT+A**: Mute/unmute microphone.
* **ALT+V**: Enable/disable camera.

### Search
* **ALT+I**: Open a list of chat search results.
* **F3**: Go to the next search result in the chat.
* **shift+F3**: Go to the previous search result in the chat.

### Settings & Miscellaneous
* **NVDA+ALT+U**: Open UnigramAccess settings window.
* **ALT+U**: Toggle progress bar announcements.
* **ALT+H**: Show a list of all UnigramAccess shortcuts.

## Changes in version 1.0.0

* Initial official release of **UnigramAccess**.
* Complete modular architecture rewrite: The main `AppModule` class in `unigram.py` now acts as a central router that elegantly delegates logic to specialized helper modules (`unigram_ui`, `unigram_navigation`, `unigram_calls`, `unigram_messages`, and `unigram_media`), making the codebase highly organized and maintainable. State trackers and overlay classes are also cleanly separated.
* Full compatibility with modern NVDA releases (NVDA 2025.1 through 2026+) and Python 3.12+.
* Independent configuration system via `UnigramAccess.ini`.
* 35+ dedicated accessibility hotkeys for fast navigation, chat lists, messages, folders, topics, and profiles.
* Comprehensive audio message interaction: playback control, speed adjustment, and rewind/fast-forward.
* Live chat monitoring (`ALT+L`) and realtime chat activity announcements (`ALT+T`).
* Streamlined voice and video call controls with accessible status notifications.
* Quick text popup viewer (`ALT+C`) and instant message actions (reply, edit, forward, delete).
* Note: UnigramAccess is an independent, modernized continuation and fork of the legacy UnigramPlus add-on originally developed by Kostya Gladkiy.
