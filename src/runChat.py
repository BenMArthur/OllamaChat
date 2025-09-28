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
        shortcut.save()

def run():
    Chat.Main(appName)
import ctypes
appName = "ollamaChat"
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appName)

addStartup()
keyboard.add_hotkey('alt+space', run)
keyboard.wait()
#fix sys prompt to always use if no other
#change delims when they are changed

#pyinstaller --onefile --noconsole --name OllamaChat src/runChat.py