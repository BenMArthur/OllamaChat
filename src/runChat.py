from PyQt5.QtCore import QThread

from Chat import Chat

import os
import sys
import winshell
from win32com.client import Dispatch
import keyboard

# Function to add the program to Windows startup
def addStartup():
    startup = winshell.startup()
    exe_path = sys.executable
    shortcut_path = os.path.join(startup, f"{appName}.lnk")
    if not os.path.exists(shortcut_path):
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = exe_path
        shortcut.WorkingDirectory = os.path.dirname(exe_path)
        shortcut.IconLocation = exe_path
        shortcut.WindowStyle = 7
        shortcut.save()

def run():
    Chat.Main(appName)
import ctypes
appName = "ollamaChat"
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appName)

addStartup()
keyboard.add_hotkey('alt+space', run)
keyboard.wait()

#add comments
#close with alt+space

#cannot remove default
#want to change default to ""

#pyinstaller --onefile --add-data=./src/img/:./img/ --noconsole -i ./src/img/icon.ico --name OllamaChat src/runChat.py