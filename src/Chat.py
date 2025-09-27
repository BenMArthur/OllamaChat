import sys
import re
import threading
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QComboBox, QPushButton, QLineEdit
)
from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor
from PyQt5.QtCore import Qt
from ollama import chat

from subprocess import run
from Settings import Settings
import os
import atexit

class Chat(QMainWindow):
    def Main():
        models = run("ollama list", capture_output=True).stdout.decode("utf-8")
        models = models.split("\n")[1:-1]
        models = [re.findall(r"\S+", item)[0] for item in models]
        model = models[0]

        app = QApplication(sys.argv)
        Chat(model, models)
        app.exec()

    def __init__(self, model, models):
        super().__init__()
        self.setWindowTitle("Chat")
        self.resize(600, 400)
        self.show()
        self.setFocus()

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.model = model
        self.prevChat = None
        self.deletingTemp = False
        self.dataStore = Path.home() / 'AppData/Roaming/OChat'
        (self.dataStore).mkdir(parents=True, exist_ok=True)
        atexit.register(self.exit_handler)

        # Top bar
        def topBar():
            top_layout = QHBoxLayout()

            # left aligned
            self.historySelect = QComboBox(editable=True)
            self.historySelect.setFixedWidth(18)
            self.historySelect.view().setMinimumWidth(146)
            self.historyNames = [path.name[:-4] for path in list(sorted((self.dataStore / f"history").glob('*.txt')))]
            self.historySelect.currentIndexChanged.connect(self.loadChat)
            top_layout.addWidget(self.historySelect)

            self.historyInput = QLineEdit()
            self.historyInput.setFixedWidth(125)
            top_layout.addWidget(self.historyInput)

            self.saveButton = QPushButton(text="💾")
            self.saveButton.setFixedWidth(27)
            self.saveButton.clicked.connect(self.saveChat)
            top_layout.addWidget(self.saveButton)

            self.deleteButton = QPushButton(text="❌")
            self.deleteButton.setFixedWidth(27)
            self.deleteButton.clicked.connect(self.deleteChat)
            top_layout.addWidget(self.deleteButton)

            self.newButton = QPushButton(text="📖")
            self.newButton.setFixedWidth(27)
            self.newButton.clicked.connect(self.newChat)
            top_layout.addWidget(self.newButton)

            # right aligned
            top_layout.addStretch(1)

            self.modelSelect = QComboBox()
            self.modelSelect.setFixedWidth(180)
            self.modelSelect.addItems(models)
            self.modelSelect.setCurrentText(model)
            self.modelSelect.currentIndexChanged.connect(self.changeModel)

            self.settingsButton = QPushButton(text="⚙")
            self.settingsButton.setFixedWidth(27)
            self.settingsButton.clicked.connect(self.toggleSettings)
            self.settings = Settings(self.dataStore)
            self.settings.submitted.connect(self.fetchSettings)
            self.fetchSettings()

            top_layout.addWidget(self.modelSelect)
            top_layout.addWidget(self.settingsButton)
            layout.addLayout(top_layout)
        topBar()
        # Chat display
        def createChatDisplay():
            self.chat_display = QTextEdit()
            self.chat_display.setAcceptRichText(False)
            self.chat_display.setLineWrapMode(QTextEdit.WidgetWidth)
            self.chat_display.installEventFilter(self)
            layout.addWidget(self.chat_display)
        createChatDisplay()

        self.newChat()

    def fetchSettings(self):
        """settings = {"enableSysPrompt": self.enableSysPrompt.isChecked(),
                    "hideSysPrompt": self.hideSysPrompt.isChecked(), "sysPrompt": self.sysPromptInput.toPlainText(),
                    "loadFixedModel": self.defaultModelRadioFixed.isChecked(),
                    "selectedModel": self.modelSelect.currentText()}"""
        self.delims = {"user": f"{self.settings.settings["delimUser"]}:",
                       "assistant": f"{self.settings.settings["delimAssistant"]}:",
                       "system": f"{self.settings.settings["delimSystem"]}:"}
        pass

    def saveChat(self):
        currentIndex = self.historySelect.currentIndex()
        newName = self.historyInput.text()
        i=0
        while newName in [self.historyNames[i] for i in range(len(self.historyNames)) if i != currentIndex]:
            i+=1

            if f"{newName}({i})" not in self.historyNames:
                newName = f"{self.historyInput.text()} ({i})"

        if (self.dataStore / f"history/{self.historyNames[currentIndex]}.txt").is_file():
            Path.rename(self.dataStore / f"history/{self.historyNames[currentIndex]}.txt", self.dataStore / f"history/{newName}.txt")
        else:
            (self.dataStore / "history").mkdir(parents=True, exist_ok=True)
            with open(self.dataStore / f"history/{newName}.txt", "w") as file:
                pass

        with open(self.dataStore / f"history/{newName}.txt", "w") as file:
            file.write(self.chat_display.toPlainText())

        self.historySelect.clear()
        self.historyNames[currentIndex] = newName
        self.historySelect.addItems(self.historyNames)
        self.historyInput.setText(newName)
        self.historySelect.setCurrentIndex(currentIndex)

    def saveTemp(self):
        (self.dataStore / f"history/temp{os.getpid()}").mkdir(parents=True, exist_ok=True)
        with open(self.dataStore / f"history/temp{os.getpid()}/{self.prevChat}.txt", "w") as file:
            file.write(self.chat_display.toPlainText())
        pass

    def loadChat(self):
        if self.prevChat is not None and not self.deletingTemp:
            self.saveTemp()
        self.deletingTemp = False

        self.historyInput.setText(self.historyNames[self.historySelect.currentIndex()])
        if (self.dataStore / f"history/temp{os.getpid()}/{self.historyNames[self.historySelect.currentIndex()]}.txt").is_file():
            with open(self.dataStore / f"history/temp{os.getpid()}/{self.historyNames[self.historySelect.currentIndex()]}.txt", "r") as file:
                self.chat_display.clear()
                self.display_text(file.read())
        elif (self.dataStore / f"history/{self.historyNames[self.historySelect.currentIndex()]}.txt").is_file():
            with open(self.dataStore / f"history/{self.historyNames[self.historySelect.currentIndex()]}.txt", "r") as file:
                self.chat_display.clear()
                self.display_text(file.read())
        else:
            self.chat_display.clear()
        self.recolour_text()
        self.prevChat = self.historyNames[self.historySelect.currentIndex()]
        self.chat_display.setFocus()

    def deleteChat(self):
        nameToDelete = self.historySelect.currentText()

        self.chat_display.clear()
        if (self.dataStore / f"history/{nameToDelete}.txt").is_file():
            (self.dataStore / f"history/{nameToDelete}.txt").unlink()
        if (self.dataStore / f"history/temp{os.getpid()}/{nameToDelete}.txt").is_file():
            self.deletingTemp = True
            (self.dataStore / f"history/temp{os.getpid()}/{nameToDelete}.txt").unlink()

        self.historyNames.remove(nameToDelete)
        if len(self.historyNames) == 0:
            self.newChat()
            pass
        self.historySelect.clear()
        self.historySelect.addItems(self.historyNames)

    def newChat(self):
        self.historyNames.insert(0, None)
        default = "new chat 1"
        i = 1
        while default in self.historyNames:
            default = f"{default[:-1]}{str(i)}"
            i += 1
        self.historyNames[0] = default
        self.chat_display.clear()
        self.historySelect.clear()
        self.historySelect.addItems(self.historyNames)

        if self.settings.settings["enableSysPrompt"] and not self.settings.settings["hideSysPrompt"]:
            self.display_text(f"{self.delims["system"]} {self.settings.settings["sysPrompt"]}\n\n")

        self.display_text(f"{self.delims["user"]} ")
        self.recolour_text()
        self.chat_display.setFocus()

    def toggleSettings(self, checked):
        if self.settings.isVisible():
            self.settings.hide()
        else:
            self.settings.show()

    def changeModel(self):
        self.model = self.modelSelect.currentText()

    def recolour_text(self):
        text = self.chat_display.toPlainText().lower()
        cursor = self.chat_display.textCursor()
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(QTextCharFormat())  # reset formatting

        pattern = re.compile(f"({self.delims["user"]}|{self.delims["assistant"]}|{self.delims["system"]})")
        matches = list(pattern.finditer(text))

        for i, match in enumerate(matches):
            role_text = match.group().lower()
            role_color = None
            if self.delims["user"] in role_text:
                role_color = QColor("blue")
            elif self.delims["assistant"] in role_text:
                role_color = QColor("green")
            elif self.delims["system"] in role_text:
                role_color = QColor("gray")

            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            fmt = QTextCharFormat()
            fmt.setForeground(role_color)
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            cursor.setCharFormat(fmt)

    def display_text(self, text, end=""):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text + end)
        self.chat_display.ensureCursorVisible()

    def eventFilter(self, obj, event):
        if obj is self.chat_display and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Return and event.modifiers() == Qt.ShiftModifier:
                self.prompt()
                return True
            elif event.key() == Qt.Key_Space:
                self.recolour_text()
        return super().eventFilter(obj, event)

    def prompt(self):
        prompt = self.chat_display.toPlainText().strip()
        prompt = re.split((f"({self.delims["user"]}|{self.delims["assistant"]}|{self.delims["system"]})"), prompt, re.IGNORECASE)[1:]

        if self.settings.settings["enableSysPrompt"] and self.settings.settings["hideSysPrompt"] and not prompt[0].startswith(self.delims["system"]):
            self.prompt.insert(0, self.settings.settings["sysPrompt"])
            #save sys prompt with file, decide whether to show it when loading

        if len(prompt) < 2:
            return
        history = []
        for counter in range(0, len(prompt), 2):
            if counter + 1 < len(prompt):
                role = None
                if prompt[counter].lower().startswith(self.delims["user"]):
                    role = "user"
                elif prompt[counter].lower().startswith(self.delims["assistant"]):
                    role = "assistant"
                elif prompt[counter].lower().startswith(self.delims["system"]):
                    role = "system"
                foundImage = re.search(r"\"[A-Z]:[\\/].+\"", prompt[counter + 1])
                if foundImage:
                    path = foundImage.group(0).strip('"')
                    prompt[counter + 1] = prompt[counter + 1].replace(match.group(0), '')
                else:
                    path = None
                if path:
                    history.append({"role": role, "content": prompt[counter + 1].strip("\n "), "images": [path]})
                else:
                    history.append({"role": role, "content": prompt[counter + 1].strip("\n ")})

        threading.Thread(target=self.generateResponse, args=[history], daemon=True).start()

    def generateResponse(self, history):
        try:
            self.display_text(f"\n\n{self.delims["assistant"]} ")
            self.recolour_text()
            stream = chat(
                model=self.model,
                messages=history,
                stream=True,
            )
            for chunk in stream:
                self.display_text(chunk['message']['content'], end="")
            self.display_text(f"\n\n{self.delims["user"]} ")
            self.recolour_text()
        except Exception as e:
            self.display_text(f"\n{e}")

    def exit_handler(self):
        path = self.dataStore / f"history/temp{os.getpid()}"
        if path.is_dir():
            for child in path.iterdir():
                if child.is_file():
                    child.unlink()
                else:
                    rm_tree(child)
            path.rmdir()


if __name__ == "__main__":
    Chat.Main()