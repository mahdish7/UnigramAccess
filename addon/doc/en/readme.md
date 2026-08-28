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

## Hotkey list:
* ALT+1: Move focus to chat list;
* ALT+2: Move focus to the last message in an open chat;
* ALT+3: Move focus to "unread messages" label;
* ALT+D: Move the focus to the edit field. If the focus is already in the edit field, then after pressing the hotkey, it will move to where it was before;
* ALT+T: Announce the name and status of an open chat;
* space: Play/stop the focused voice or video message, or open a media file attached to the current message;
* ALT+P: Play/pause the voice message currently playing;
* ALT+S: Increase/decrease the playback speed of voice messages;
* ALT+E: Close audio player;
* control+C: Copy the message if it contains text. If the focus is on a link, the link will be copied.
* ALT+shift+C: Call if it's a contact, or enter a voice chat if it's a group;
* ALT+shift+V: Press the video call button;
* ALT+Y: Accept call;
* ALT+N: Press the \"Decline call\" button if there is an incoming call, the \"End call\" button if the call is in progress, or leave the voice chat if it is active;
* ALT+A: Press \"Mute/unmute microphone\" button;
* ALT+V: Press "Enable/disable camera" button;
* ALT+Q: Press \"Instant view\" button, if it is included in the current message;
* ALT+M: Open navigation menu;
* control+R: Start/stop voice message recording;
* control+D: If pressed once, cancels the recording of a voice message. If pressed twice, changes the notification type when starting, sending, or canceling a voice message recording;
* ALT+U: Toggle progress bar announcements;
* control+P: Open current chat profile;
* delete: Delete a message or chat;
* shift+delete: Delete message or chat from both sides;
* control+ALT+C: Open comments;
* enter: Reply to message;
* ALT+F: Forward message;
* backspace: Edit message;
* ALT+shift+R: Mark a chat as read;
* control+space: Switch to selection mode;
* ALT+shift+L: Copy data for broadcasting to the clipboard;
* ALT+C: Show message text in popup window.
* NVDA+ALT+U: Open UnigramAccess settings window
* ALT+4: Move focus to list of chat folders.
* control+shift+A: Press "Attach file" button.
* control+N: Press "New chat" button.
* Unassigned: Pin a message or chat.
* ALT+5: Move focus to open profile.
* ALT+L: Enable automatic reading of new messages in the current chat.
* NVDA+ALT+R: Convert voice message to text.
* Left arrow: Announce the original message, the message that was replied to. Double-pressing moves focus to that message.
* ALT+6: Move focus to the list of group threads.
* ALT+H: Show a list of all UnigramAccess shortcuts.
* ALT+I: Open a list of chat search results.
* ALT+J: Go to the previous search result in the chat.
* ALT+K: Go to the next search result in the chat.

## Changes in version 1.0.0

* Initial official release of **UnigramAccess**.
* Complete modular architecture rewrite with clean separation of overlay classes (`overlays.py`), state trackers (`trackers.py`), and core application logic (`unigram.py`).
* Full compatibility with modern NVDA releases (NVDA 2024.1 through 2026+) and Python 3.12+.
* Independent configuration system via `UnigramAccess.ini`.
* 35+ dedicated accessibility hotkeys for fast navigation, chat lists, messages, folders, topics, and profiles.
* Comprehensive audio message interaction: playback control, speed adjustment, and rewind/fast-forward.
* Live chat monitoring (`ALT+L`) and realtime chat activity announcements (`ALT+T`).
* Streamlined voice and video call controls with accessible status notifications.
* Quick text popup viewer (`ALT+C`) and instant message actions (reply, edit, forward, delete).
* Note: UnigramAccess is an independent, modernized continuation and fork of the legacy UnigramPlus add-on originally developed by Kostya Gladkiy.
