import threading

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QComboBox, QLabel, QLineEdit, QCheckBox, QRadioButton, QPushButton
)
from PyQt5.QtCore import pyqtSignal
from ollama import list as ollamaList
import json

from LoadImage import resource_path


class Settings(QWidget):
    submitted = pyqtSignal(str)

    def __init__(self, dataStore, screen):
        super().__init__()
        self.dataStore = dataStore
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
            self.sysPromptLabel = QLabel("\nDefault Sytem prompt: \n     (Not useful for some models i.e. deepseek) \n     (added at the start of any chat without explicit sysPrompt)")
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

            return submissionLayout
        layout.addLayout(bottom())

        self.setLayout(layout)
        #just locks size, cannot get smaller than elements
        self.setFixedSize(0,0)
        threading.Thread(target=self.loadSettings(True)).start()

    def submit(self):
        delimUser = self.delimUserInput.text().lower()
        delimAssistant = self.delimAssistantInput.text().lower()
        delimSystem = self.delimSystemInput.text().lower()
        if (not delimUser != delimAssistant != delimSystem
                or any([len(x)==0 for x in [delimUser, delimAssistant, delimSystem]])):
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

    def movedOrResized(self, pos, size):
        self.settings["pos"] = (pos.x(), pos.y())
        self.settings["size"] = (size.width(), size.height())
        self.saveSettingsFile()