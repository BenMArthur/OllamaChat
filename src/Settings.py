from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QComboBox, QLabel, QLineEdit, QCheckBox, QRadioButton, QPushButton
)
from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor
from PyQt5.QtCore import Qt, pyqtSignal
from subprocess import run
import re
import json


class Settings(QWidget):
    submitted = pyqtSignal(str)

    def __init__(self, dataStore):
        super().__init__()
        layout = QVBoxLayout()
        self.dataStore = dataStore
        self.defaults = {"delimUser": "user", "delimAssistant": "assistant", "delimSystem": "system",
                        "enableSysPrompt": False, "hideSysPrompt": False, "sysPrompt": "", "loadFixedModel": False,
                        "selectedModel": ""}
        self.settings = self.defaults

        self.setWindowTitle("Settings")

        def delim():
            delimLayout = QVBoxLayout()
            self.delimLabel = QLabel("Delimiters: \n     (\":\" automatically inserted at end, capitalisation not important)")
            delimLayout.addWidget(self.delimLabel)

            delimUserLayout = QHBoxLayout()
            self.delimUserLabel = QLabel("     Prompt/You:")
            self.delimUserInput = QLineEdit()
            self.delimUserInput.setFixedWidth(125)
            self.delimUserPost = QLabel(":")
            delimUserLayout.addWidget(self.delimUserLabel)
            delimUserLayout.addWidget(self.delimUserInput)
            delimUserLayout.addWidget(self.delimUserPost)
            delimUserLayout.addStretch(1)

            delimAssistantLayout = QHBoxLayout()
            self.delimAssistantLabel = QLabel("     Response/AI:")
            self.delimAssistantInput = QLineEdit()
            self.delimAssistantInput.setFixedWidth(125)
            self.delimAssistantPost = QLabel(":")
            delimAssistantLayout.addWidget(self.delimAssistantLabel)
            delimAssistantLayout.addWidget(self.delimAssistantInput)
            delimAssistantLayout.addWidget(self.delimAssistantPost)
            delimAssistantLayout.addStretch(1)

            delimSystemLayout = QHBoxLayout()
            self.delimSystemLabel = QLabel("     System:")
            self.delimSystemInput = QLineEdit()
            self.delimSystemInput.setFixedWidth(125)
            self.delimSystemPost = QLabel(":")
            delimSystemLayout.addWidget(self.delimSystemLabel)
            delimSystemLayout.addWidget(self.delimSystemInput)
            delimSystemLayout.addWidget(self.delimSystemPost)
            delimSystemLayout.addStretch(1)

            delimLayout.addLayout(delimUserLayout)
            delimLayout.addLayout(delimAssistantLayout)
            delimLayout.addLayout(delimSystemLayout)

            return delimLayout
        delimLayout = delim()

        def sysPrompt():
            SysPromptLayout = QVBoxLayout()
            self.sysPromptLabel = QLabel("\nDefault Sytem prompt: \n     (Not useful for some models i.e. deepseek)")
            SysPromptLayout.addWidget(self.sysPromptLabel)

            self.enableSysPrompt = QCheckBox("Enable default system prompt", self)
            SysPromptLayout.addWidget(self.enableSysPrompt)
            self.hideSysPrompt = QCheckBox("Hide default system prompt", self)
            SysPromptLayout.addWidget(self.hideSysPrompt)

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
        SysPromptLayout = sysPrompt()

        def defaultModel():
            defaultModelLayout = QVBoxLayout()
            self.defaultModelLabel = QLabel("\nWhat model will be selected when window is opened:")
            defaultModelLayout.addWidget(self.defaultModelLabel)

            self.defaultModelRadioVar = QRadioButton("Model used in previous prompt")
            defaultModelLayout.addWidget(self.defaultModelRadioVar)
            defaultModelRadioFixedLayout = QHBoxLayout()
            self.defaultModelRadioFixed = QRadioButton("Fixed model:")
            models = run("ollama list", capture_output=True).stdout.decode("utf-8")
            models = models.split("\n")[1:-1]
            self.models = [re.findall(r"\S+", item)[0] for item in models]
            self.modelSelect = QComboBox()
            self.modelSelect.addItems(self.models)
            self.modelSelect.setFixedWidth(180)
            defaultModelRadioFixedLayout.addWidget(self.defaultModelRadioFixed)
            defaultModelRadioFixedLayout.addWidget(self.modelSelect)
            defaultModelRadioFixedLayout.addStretch(1)
            defaultModelLayout.addLayout(defaultModelRadioFixedLayout)

            return defaultModelLayout
        defaultModelLayout = defaultModel()

        submissionLayout = QHBoxLayout()
        submissionLayout.addStretch(1)
        self.resetButton = QPushButton(text="Reset to defaults")
        self.resetButton.clicked.connect(self.reset)
        submissionLayout.addWidget(self.resetButton)
        self.submissionButton = QPushButton(text="Save changes")
        self.submissionButton.clicked.connect(self.submit)
        submissionLayout.addWidget(self.submissionButton)


        self.setLayout(layout)
        layout.addLayout(delimLayout)
        layout.addLayout(SysPromptLayout)
        layout.addLayout(defaultModelLayout)
        layout.addLayout(submissionLayout)
        layout.addStretch(1)
        self.loadSettings(True)

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
                         "selectedModel": self.modelSelect.currentText()}
        try:
            with open(self.dataStore / f"settings.json", "w") as file:
                json.dump(self.settings, file)
        except Exception as e:
            print(e)
        self.hide()
        self.submitted.emit("New settings")

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