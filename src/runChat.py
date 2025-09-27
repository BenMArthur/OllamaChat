import keyboard
import subprocess
import os
from Chat import Chat
from threading import Thread


def run():
    #Thread(target=Chat.Main).start()
    Chat.Main()

# Listen for Shift + Space
keyboard.add_hotkey('shift+space', run)
keyboard.wait()  # Keeps the script running

#pyinstaller --onefile --noconsole runChat.py