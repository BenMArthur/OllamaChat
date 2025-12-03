import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading

import winshell
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QComboBox, QLabel, QLineEdit, QCheckBox, QRadioButton, QPushButton, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, QTimer
from ollama import list as ollamaList
import json

from LoadImage import resource_path


class Settings(QWidget):
    submitted = pyqtSignal(str)

    def __init__(self, dataStore, screen, appname):
        super().__init__()
        self.dataStore = dataStore
        self.appName = appname
        self.defaults = {"delimUser": "user", "delimAssistant": "assistant", "delimSystem": "system",
                        "enableSysPrompt": False, "hideSysPrompt": False, "sysPrompt": "", "loadFixedModel": False,
                        "selectedModel": "", "prevModel": "", "pos": (screen.width()//2-300, screen.height()//2-150), "size": (600, 300)}
        self.settings = self.defaults

        layout = QVBoxLayout()
        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon(resource_path("img/settings.png")))

        #section of settings concerning the delimiters
        def delim():
            def delimItem(text):
                tempLayout = QHBoxLayout()
                label = QLabel(text)
                input = QLineEdit()
                input.setFixedWidth(125)
                post = QLabel(":")
                tempLayout.addWidget(label)
                tempLayout.addWidget(input)
                tempLayout.addWidget(post)
                tempLayout.addStretch(1)
                delimLayout.addLayout(tempLayout)

                return tempLayout, input

            delimLayout = QVBoxLayout()

            self.delimLabel = QLabel("Delimiters: \n     (\":\" automatically inserted at end, capitalisation not important)")
            delimLayout.addWidget(self.delimLabel)

            delimUserLayout, self.delimUserInput = delimItem("     Prompt/You:")
            delimAssistantLayout, self.delimAssistantInput = delimItem("     Response/AI:")
            delimSystemLayout, self.delimSystemInput = delimItem("     System:")

            return delimLayout
        layout.addLayout(delim())

        #default system prompt section
        def sysPrompt():
            SysPromptLayout = QVBoxLayout()
            self.sysPromptLabel = QLabel("\nDefault Sytem prompt: \n"
                                         "     (Not useful for some models i.e. deepseek) \n"
                                         "     (added at the start of any chat without explicit sysPrompt) \n"
                                         "     (Default prompt can only be edited here, even if showing it)")
            SysPromptLayout.addWidget(self.sysPromptLabel)

            def checkItem(text):
                layout = QHBoxLayout()
                layout.addWidget(QLabel("   "))
                box = QCheckBox(text, self)
                layout.addWidget(box)
                layout.addStretch(1)
                SysPromptLayout.addLayout(layout)
                return box

            self.enableSysPrompt = checkItem("Enable default system prompt")
            self.hideSysPrompt = checkItem("Hide default system prompt")

            sysPromptInputLayout = QHBoxLayout()
            SysPromptLabelLayout = QVBoxLayout()
            self.sysPromptLabel = QLabel("     Prompt:")
            self.sysPromptInput = QTextEdit()
            self.sysPromptInput.setFixedHeight(100)
            self.sysPromptInput.setAcceptRichText(False)
            self.sysPromptInput.setLineWrapMode(QTextEdit.WidgetWidth)
            SysPromptLabelLayout.addWidget(self.sysPromptLabel)
            SysPromptLabelLayout.addStretch(1)
            sysPromptInputLayout.addLayout(SysPromptLabelLayout)
            sysPromptInputLayout.addWidget(self.sysPromptInput)
            SysPromptLayout.addLayout(sysPromptInputLayout)

            return SysPromptLayout
        layout.addLayout(sysPrompt())

        #default model section
        def defaultModel():
            defaultModelLayout = QVBoxLayout()
            self.defaultModelLabel = QLabel("\nWhat model will be selected when window is opened:")
            defaultModelLayout.addWidget(self.defaultModelLabel)

            self.defaultModelRadioVar = QRadioButton("Model used in previous prompt")
            defaultModelLayout.addWidget(self.defaultModelRadioVar)

            defaultModelRadioFixedLayout = QHBoxLayout()
            self.defaultModelRadioFixed = QRadioButton("Fixed model:")
            self.models = [str(model.model) for model in ollamaList().models]
            self.modelSelect = QComboBox()
            self.modelSelect.addItems(self.models)
            self.modelSelect.setFixedWidth(180)
            defaultModelRadioFixedLayout.addWidget(self.defaultModelRadioFixed)
            defaultModelRadioFixedLayout.addWidget(self.modelSelect)
            defaultModelRadioFixedLayout.addStretch(1)

            defaultModelLayout.addLayout(defaultModelRadioFixedLayout)

            return defaultModelLayout
        layout.addLayout(defaultModel())

        #create the reset and submit buttons
        def bottom():
            submissionLayout = QHBoxLayout()
            submissionLayout.addStretch(1)

            self.resetButton = QPushButton(text="Reset to defaults")
            self.resetButton.clicked.connect(self.reset)
            submissionLayout.addWidget(self.resetButton)

            self.submissionButton = QPushButton(text="Save changes")
            self.submissionButton.clicked.connect(self.submit)
            submissionLayout.addWidget(self.submissionButton)

            self.closeButton = QPushButton(text="⏻")
            self.closeButton.setFixedWidth(27)
            self.closeButton.setStyleSheet("color: red; font-weight: bold;")
            submissionLayout.addWidget(self.closeButton)
            self.closeButton.clicked.connect(self.confirmExit)

            return submissionLayout
        layout.addLayout(bottom())

        self.setLayout(layout)
        #just locks size, cannot get smaller than elements
        self.setFixedSize(0,0)
        threading.Thread(target=self.loadSettings(True)).start()

    # --- Function that shows a warning and exits ---
    def confirmExit(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Exit Program")
        msg.setText("This will fully exit the program.\nThe program will stop running on startup.\nThe exe must be re-ran to use again.")
        # Add three custom buttons
        yes_btn = msg.addButton("Exit", QMessageBox.AcceptRole)
        no_btn = msg.addButton("Cancel", QMessageBox.RejectRole)
        uninstall_btn = msg.addButton("Uninstall", QMessageBox.DestructiveRole)
        uninstall_btn.setStyleSheet("color: red;")

        msg.exec_()

        # Determine which was clicked
        clicked = msg.clickedButton()

        if clicked == yes_btn:
            startup = winshell.startup()
            shortcut_path = os.path.join(startup, f"{self.appName}.lnk")
            os.remove(shortcut_path)
            sys.exit(0)
        elif clicked == no_btn:
            pass  # Do nothing
        elif clicked == uninstall_btn:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Uninstall Program")
            msg.setText("This will delete the application and all other files.")
            # Add three custom buttons
            limited_btn = msg.addButton("Leave history and settings", QMessageBox.AcceptRole)
            cancel_btn = msg.addButton("Cancel", QMessageBox.RejectRole)
            full_btn = msg.addButton("Delete everything", QMessageBox.DestructiveRole)

            limited_btn.setEnabled(False)
            full_btn.setEnabled(False)
            timer = QTimer(msg)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: (limited_btn.setEnabled(True), full_btn.setEnabled(True)))
            timer.start(3000)

            msg.exec_()
            clicked = msg.clickedButton()

            if clicked == cancel_btn:
                pass
            elif clicked == full_btn:
                if os.path.isdir(self.dataStore):
                    shutil.rmtree(self.dataStore)
            elif clicked == limited_btn or clicked == full_btn:
                startup = winshell.startup()
                shortcut_path = os.path.join(startup, f"{self.appName}.lnk")
                os.remove(shortcut_path)

                exe_path = sys.argv[0]
                name = exe_path.split("\\")[-1].lower()
                name = name.split(".")
                if name[-1] == "exe" and "python" not in ".".join(name):
                    # Create a temporary batch file
                    bat_file = tempfile.NamedTemporaryFile(delete=False, suffix=".bat").name
                    # Write the batch commands
                    with open(bat_file, "w") as f:
                        f.write(f"""
                        @echo off
                        timeout /t 5 > nul
                        del "{exe_path}"
                        del "{bat_file}"
                        """)
                    # Run the batch file silently
                    subprocess.Popen(
                        ['cmd', '/c', bat_file],
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                # Exit the PyQt application
                sys.exit()


    def updateModels(self, models):
        self.models = models
        self.modelSelect.clear()
        self.modelSelect.addItems(self.models)


    def submit(self):
        delimUser = self.delimUserInput.text().lower()
        delimAssistant = self.delimAssistantInput.text().lower()
        delimSystem = self.delimSystemInput.text().lower()
        if (not delimUser != delimAssistant != delimSystem
                or any([len(x)==0 for x in [delimUser, delimAssistant, delimSystem]])
                or any([":" in x for x in [delimUser, delimAssistant, delimSystem]])):
            if delimUser != self.settings["delimUser"]:
                self.delimUserInput.setText("invalid option")
            if delimAssistant != self.settings["delimAssistant"]:
                self.delimAssistantInput.setText("invalid option")
            if delimSystem != self.settings["delimSystem"]:
                self.delimSystemInput.setText("invalid option")
            return


        self.settings = {"delimUser": delimUser,
                         "delimAssistant": delimAssistant,
                         "delimSystem": delimSystem,
                         "enableSysPrompt": self.enableSysPrompt.isChecked(),
                         "hideSysPrompt": self.hideSysPrompt.isChecked(),
                         "sysPrompt": self.sysPromptInput.toPlainText(),
                         "loadFixedModel": self.defaultModelRadioFixed.isChecked(),
                         "selectedModel": self.modelSelect.currentText(),
                         "prevModel": self.settings["prevModel"],
                         "pos": self.settings["pos"],
                         "size": self.settings["size"]}
        self.saveSettingsFile()
        self.hide()
        self.submitted.emit("New settings")

    def saveSettingsFile(self):
            try:
                with open(self.dataStore / f"settings.json", "w") as file:
                    json.dump(self.settings, file)
            except Exception as e:
                print(e)

    def loadSettings(self, checkFile):
        if checkFile:
            try:
                if (self.dataStore / f"settings.json").is_file():
                    with open(self.dataStore / f"settings.json", "r") as file:
                        self.settings = json.load(file)
            except Exception as e:
                print(e)
                pass
            if len(self.settings.keys()) != len(self.defaults):
                self.settings = self.defaults

        self.delimUserInput.setText(self.settings["delimUser"])
        self.delimAssistantInput.setText(self.settings["delimAssistant"])
        self.delimSystemInput.setText(self.settings["delimSystem"])
        self.enableSysPrompt.setChecked(self.settings["enableSysPrompt"])
        self.hideSysPrompt.setChecked(self.settings["hideSysPrompt"])
        self.sysPromptInput.setText(self.settings["sysPrompt"])
        if self.settings["loadFixedModel"]:
            self.defaultModelRadioFixed.setChecked(True)
        else:
            self.defaultModelRadioVar.setChecked(True)
        if self.settings["selectedModel"] in self.models:
            self.modelSelect.setCurrentText(self.settings["selectedModel"])
        else:
            self.modelSelect.setCurrentText(self.models[0])


    def reset(self):
        if (self.dataStore / f"settings.json").is_file():
            (self.dataStore / f"settings.json").unlink()
        self.loadSettings(True)

    def showEvent(self, a0):
        self.loadSettings(False)

    # open the settings menu
    def toggleSettings(self):
        try:
            if self.isVisible():
                self.hide()
            else:
                self.show()

        except Exception as e:
            self.display_text("toggleSettings: ", str(e))

    def updatePrevModel(self, model):
        self.settings["prevModel"] = model
        self.saveSettingsFile()

    def movedOrResized(self, pos, size):
        self.settings["pos"] = (pos.x(), pos.y())
        self.settings["size"] = (size.width(), size.height())
        self.saveSettingsFile()

    # get settings when they are changed
    def fetchSysPromptSettings(self, text, enableSysPrompt, hideSysPrompt, sysPrompt):
        newSysPrompt = self.settings["sysPrompt"]
        newHideSysPrompt = self.settings["hideSysPrompt"]
        newEnableSysPrompt = self.settings["enableSysPrompt"]
        delims = {"user": f"{self.settings["delimUser"]}:",
                           "assistant": f"{self.settings["delimAssistant"]}:",
                           "system": f"{self.settings["delimSystem"]}:"}
        # check if there is any changes in default prompt
        if (newSysPrompt != sysPrompt
                or newHideSysPrompt != hideSysPrompt
                or newEnableSysPrompt != enableSysPrompt):
            parts = re.split(f"({delims["user"]}|{delims["assistant"]}|{delims["system"]})", text, flags=re.IGNORECASE)[1:]
            safeToCheck = len(parts) >= 2
            started = delims["assistant"].lower() in [part.lower() for part in parts[::2]]
            # if there is a change in enabling
            if newEnableSysPrompt != enableSysPrompt:
                # if hiding sysPrompt don't have to do anything
                if not hideSysPrompt:
                    # if turning on the sysprompt
                    if newEnableSysPrompt:
                        # only change the sysprompt if the chat has not started
                        if not started:
                            # if there is enough entries to check if the default prompt is being used
                            if safeToCheck:
                                # if the current default prompt is there change it
                                if parts[0].lower() == delims["system"].lower() and parts[
                                    1] == sysPrompt:
                                    text = delims["system"] + " " + sysPrompt + "\n\n" + "".join(
                                        parts[2:])
                                else:
                                    text = delims["system"] + " " + sysPrompt + "\n\n" + text
                            # if there is not enough entries then it doesnt have a system prompt
                            else:
                                text = delims["system"] + " " + sysPrompt + "\n\n" + text
                        # do not change prompt if chat has already started
                        else:
                            pass
                    # if turning off the sysPrompt
                    else:
                        # only change if chat has been started
                        if not started:
                            if safeToCheck:
                                # if the current default prompt is there remove it
                                if parts[0].lower() == delims["system"].lower() and parts[
                                    1].strip() == sysPrompt.strip():
                                    text = "".join(parts[2:])
                            # it wont have the current Default prompt
                            else:
                                pass
                        # do nothing if the chat has started
                        else:
                            pass
                # do nothing if sysprompt is hidden
                else:
                    pass
                enableSysPrompt = newEnableSysPrompt

            # if there is a change in hiding
            # dont care whether chat has started as this doesn't affect generation
            if newHideSysPrompt != hideSysPrompt:
                # only do anything if sysprompt is enabled and there is a sysprompt
                # if it is disabled it is already hidden and won't be shown
                if enableSysPrompt:
                    # if prompt is getting shown
                    if not newHideSysPrompt:
                        # if it is safe to check for an existing prompt
                        if safeToCheck:
                            # if there is an existing sysprompt do nothing
                            if parts[0].lower() == delims["system"].lower():
                                pass
                            # else add on the default prompt
                            else:
                                text = delims["system"] + " " + sysPrompt + "\n\n" + text
                        # if it is short then it won't have a sysprompt
                        else:
                            text = delims["system"] + " " + sysPrompt + "\n\n" + text
                    # if hiding sysprompt
                    else:
                        # if it is safe to check for the prompt
                        if safeToCheck:
                            # if the current default prompt is there remove it
                            if parts[0].lower() == delims["system"].lower() and parts[
                                1].strip() == sysPrompt.strip():
                                text = "".join(parts[2:])
                            # else do nothing
                            else:
                                pass
                        # if it is short then it won't have a sysprompt
                        else:
                            pass
                hideSysPrompt = newHideSysPrompt

            # if change in the content of the prompt
            if newSysPrompt != sysPrompt:
                # only do anything if enabled and showing
                if enableSysPrompt:
                    if not hideSysPrompt:
                        # only change if the chat has started
                        if not started:
                            if safeToCheck:
                                # if the old default prompt is there replace it
                                if parts[0].lower() == delims["system"].lower() and parts[
                                    1].strip() == sysPrompt.strip():
                                    text = delims["system"] + " " + newSysPrompt + "\n\n" + "".join(
                                        parts[2:])
                            else:
                                text = delims["system"] + " " + newSysPrompt + "\n\n" + text
                        # change nothing if chat has started
                        else:
                            pass
                    # if prompt was hidden and chat is started, want to display the old prompt
                    else:
                        if started:
                            # if there is no system prompt
                            if parts[0].lower() != delims["system"].lower():
                                text = delims["system"] + " " + sysPrompt + "\n\n" + text
                sysPrompt = newSysPrompt
        return enableSysPrompt, hideSysPrompt, sysPrompt, text