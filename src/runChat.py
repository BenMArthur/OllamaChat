import queue

from Chat import Chat

import os
import sys
import winshell
from win32com.client import Dispatch
import keyboard
from threading import Lock

# Function to add the program to Windows startup
def addStartup():
    startup = winshell.startup()
    exe_path = sys.executable
    shortcut_path = os.path.join(startup, "OChat.lnk")
    if not os.path.exists(shortcut_path):
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = exe_path
        shortcut.WorkingDirectory = os.path.dirname(exe_path)
        shortcut.IconLocation = exe_path
        shortcut.save()

def run():
    if run_lock.acquire(blocking=False):
        try:
            Chat.Main()
        finally:
            run_lock.release()

# Add to startup and set hotkey
addStartup()
run_lock = Lock()

"""tasks = queue.Queue()
def schedule_run():
    tasks.put(run)
keyboard.add_hotkey('alt+space', schedule_run)
while True:
    func = tasks.get()  # blocks until something scheduled
    func()"""
keyboard.add_hotkey('alt+space', run)
keyboard.wait()


#pyinstaller --onefile --noconsole --name OChat src/runChat.py
