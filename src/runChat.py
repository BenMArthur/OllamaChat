from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

from Chat import Chat

import os
import sys
import winshell
from win32com.client import Dispatch
import keyboard
import ctypes
import threading
import subprocess

appName = "ollamaChat"

def already_running(appName):
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, appName)
    last_error = ctypes.windll.kernel32.GetLastError()
    if last_error == 183:  # ERROR_ALREADY_EXISTS
        return True
    return False
if already_running(appName):
    sys.exit(0)


ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appName)
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
addStartup()


CREATE_NO_WINDOW = 0x08000000
subprocess.Popen(["ollama", "serve"], creationflags=CREATE_NO_WINDOW)
app = QApplication(sys.argv)
font = QFont("Arial", 11)
app.setFont(font)
chat = Chat(app.primaryScreen().availableGeometry(), appName)

def hotkey_listener():
    keyboard.add_hotkey('ctrl+alt+space', lambda: chat.toggleSignal.emit())
    keyboard.wait()
threading.Thread(target=hotkey_listener, daemon=True).start()


app.exec()

#add comments

#pyinstaller --onefile --add-data=./src/img/:./img/ --noconsole -i ./src/img/icon.ico --name OllamaChat src/runChat.py