import sys
import re
from pathlib import Path

from PyQt5.Qt import Qt
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QComboBox, QHBoxLayout, QLineEdit, \
    QPushButton, QTextEdit
from PyQt5.QtCore import QObject, QThreadPool, pyqtSignal, QThread, QTimer
from ollama import chat
from ollama import list as ollamaList
from Settings import Settings
import os
import atexit
import threading
import time

class PromptWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)

    def __init__(self, chat, history):
        super().__init__()
        self.chat = chat
        self.history = history

    def run(self):
        try:
            self.chat.settings.settings["prevModel"] = self.chat.model
            self.chat.settings.saveSettingsFile()

            self.progress.emit("assis12")
            stream = chat(
                model=self.chat.model,
                messages=self.history,
                stream=True,
            )
            for chunk in stream:
                #self.chat.display_text(chunk['message']['content'], end="")
                self.chunk = chunk['message']['content']
                self.progress.emit(self.chunk)
            self.progress.emit("usr12")
            self.chat.prompting = False

        except Exception as e:
            self.chat.display_text("toggleSettings: ", str(e))
        self.finished.emit()

class Chat(QMainWindow):

    @staticmethod
    def Main():
        app = QApplication(sys.argv)
        Chat(app.primaryScreen().availableGeometry())
        app.exec()

    newPrompt = pyqtSignal(str)
    moveOrResize = pyqtSignal(str)
    def __init__(self, screen):
        super().__init__()
        self.threadpool = QThreadPool()

        models = [str(model.model) for model in ollamaList().models]
        self.hiddenDefaultPrompt = None
        self.prevChat = None
        self.deletingTemp = False
        self.prompting = False
        self.dataStore = Path.home() / 'AppData/Roaming/OChat'
        self.dataStore.mkdir(parents=True, exist_ok=True)
        atexit.register(self.exit_handler)

        self.settings = Settings(self.dataStore, screen)
        self.settings.submitted.connect(self.fetchSettings)
        if self.settings.settings["loadFixedModel"]:
            self.model = self.settings.settings["selectedModel"]
        elif self.settings.settings["prevModel"] != "":
            self.model = self.settings.settings["prevModel"]
        else:
            self.model = models[0]

        #create UI
        def makeUI(models, model, pos, size):
            self.setWindowTitle("Chat")
            self.resize(size[0], size[1])
            self.move(pos[0], pos[1])
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)

            # Top bar
            def topBar(layout, models, model):
                top_layout = QHBoxLayout()

                # left aligned
                self.historySelect = QComboBox(editable=True)
                self.historySelect.setFixedWidth(18)
                self.historySelect.view().setMinimumWidth(146)
                self.historyNames = [path.name[:-4] for path in
                                     list(sorted((self.dataStore / f"history").glob('*.txt')))]
                top_layout.addWidget(self.historySelect)

                self.historyInput = QLineEdit()
                self.historyInput.setFixedWidth(125)
                top_layout.addWidget(self.historyInput)

                self.saveButton = QPushButton(text="💾")
                self.saveButton.setFixedWidth(27)
                top_layout.addWidget(self.saveButton)

                self.deleteButton = QPushButton(text="❌")
                self.deleteButton.setFixedWidth(27)
                top_layout.addWidget(self.deleteButton)

                self.newButton = QPushButton(text="📖")
                self.newButton.setFixedWidth(27)
                top_layout.addWidget(self.newButton)

                # right aligned
                top_layout.addStretch(1)

                self.modelSelect = QComboBox()
                self.modelSelect.setFixedWidth(180)
                self.modelSelect.addItems(models)
                self.modelSelect.setCurrentText(model)

                self.settingsButton = QPushButton(text="⚙")
                self.settingsButton.setFixedWidth(27)

                top_layout.addWidget(self.modelSelect)
                top_layout.addWidget(self.settingsButton)
                layout.addLayout(top_layout)

                self._move_resize_timer = QTimer()
                self._move_resize_timer.setSingleShot(True)
                self._move_resize_timer.timeout.connect(self.on_move_resize_finished)

            # Chat display
            def createChatDisplay(layout):
                self.chat_display = QTextEdit()
                self.chat_display.setAcceptRichText(False)
                self.chat_display.setLineWrapMode(QTextEdit.WidgetWidth)
                layout.addWidget(self.chat_display)

            topBar(layout, models, model)
            createChatDisplay(layout)
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.show()
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.show()
        makeUI(models, self.model, self.settings.settings["pos"], self.settings.settings["size"])
        #connect up UI
        self.historySelect.currentIndexChanged.connect(self.loadChat)
        self.saveButton.clicked.connect(self.saveChat)
        self.deleteButton.clicked.connect(self.deleteChat)
        self.newButton.clicked.connect(self.newChat)
        self.modelSelect.currentIndexChanged.connect(self.changeModel)
        self.settingsButton.clicked.connect(self.settings.toggleSettings)
        self.chat_display.installEventFilter(self)

        #emitters from UI
        self.newPrompt.connect(self.prompt)
        self.moveOrResize.connect(lambda: self.settings.movedOrResized(self.pos(), self.size()))

        self.fetchSettings()

        self.newChat()


    #get settings when they are changed
    def fetchSettings(self):
        """settings = {"enableSysPrompt": self.enableSysPrompt.isChecked(),
                    "hideSysPrompt": self.hideSysPrompt.isChecked(), "sysPrompt": self.sysPromptInput.toPlainText(),
                    "loadFixedModel": self.defaultModelRadioFixed.isChecked(),
                    "selectedModel": self.modelSelect.currentText()}"""
        try:
            self.delims = {"user": f"{self.settings.settings["delimUser"]}:",
                           "assistant": f"{self.settings.settings["delimAssistant"]}:",
                           "system": f"{self.settings.settings["delimSystem"]}:"}

        except Exception as e:
            self.display_text("fetchSettings: ", str(e))

    #save chat permenantly
    def saveChat(self):
        try:
            currentIndex = self.historySelect.currentIndex()
            newName = self.historyInput.text()
            i=0
            while newName in [self.historyNames[j] for j in range(len(self.historyNames)) if j != currentIndex]:
                i+=1
                if f"{newName}({i})" not in self.historyNames:
                    newName = f"{self.historyInput.text()} ({i})"

            if (self.dataStore / f"history/{self.historyNames[currentIndex]}.txt").is_file():
                Path.rename(self.dataStore / f"history/{self.historyNames[currentIndex]}.txt", self.dataStore / f"history/{newName}.txt")
            else:
                (self.dataStore / "history").mkdir(parents=True, exist_ok=True)
                with open(self.dataStore / f"history/{newName}.txt", "w"):
                    pass

            ToWrite = self.addHiddenPromptIfNeeded(self.chat_display.toPlainText())
            with open(self.dataStore / f"history/{newName}.txt", "w") as file:
                file.write(ToWrite)

            self.historySelect.clear()
            self.historyNames[currentIndex] = newName
            self.historySelect.addItems(self.historyNames)
            self.historyInput.setText(newName)
            self.historySelect.setCurrentIndex(currentIndex)

            self.saveTemp()

        except Exception as e:
            self.display_text("saveChat: ", str(e))

    #save chat as a temporary chat when switching away
    def saveTemp(self):
        try:
            (self.dataStore / f"history/temp{os.getpid()}").mkdir(parents=True, exist_ok=True)

            ToWrite = self.addHiddenPromptIfNeeded(self.chat_display.toPlainText())
            with open(self.dataStore / f"history/temp{os.getpid()}/{self.prevChat}.txt", "w") as file:
                file.write(ToWrite)

        except Exception as e:
            self.display_text("saveTemp: ", str(e))

    def splitText(self, text):
        try:
            return re.split(f"({self.delims["user"]}|{self.delims["assistant"]}|{self.delims["system"]})", text, flags=re.IGNORECASE)[1:]
        except Exception as e:
            self.display_text("splitText: ", str(e))

    def addHiddenPromptIfNeeded(self, text):
        try:
            if text:
                split = self.splitText(text)
                if len(split)>0:
                    if not split[0].startswith(self.delims["system"]) and self.hiddenDefaultPrompt:
                        text = f"{self.delims["system"]} {self.hiddenDefaultPrompt}\n\n{text}"
                return text
            return ""

        except Exception as e:
            self.display_text("addHiddenPromptIfNeeded: ", str(e))

    #load the chat selected in the dropdown
    def loadChat(self):
        try:
            if self.prevChat is not None and not self.deletingTemp:
                self.saveTemp()
            self.deletingTemp = False

            self.historyInput.setText(self.historyNames[self.historySelect.currentIndex()])
            if (self.dataStore / f"history/temp{os.getpid()}/{self.historyNames[self.historySelect.currentIndex()]}.txt").is_file():
                with open(self.dataStore / f"history/temp{os.getpid()}/{self.historyNames[self.historySelect.currentIndex()]}.txt", "r") as file:
                    self.chat_display.clear()
                    text = file.read()
                    split = self.splitText(text)
                    if len(split) >= 2:
                        if split[0].startswith(self.delims["system"]) and self.hiddenDefaultPrompt is not None:
                            if split[1].strip() == self.hiddenDefaultPrompt.strip():
                                self.display_text("".join(split[2:]))
                        else:
                            self.display_text(text)
                    else:
                        self.display_text(text)
            elif (self.dataStore / f"history/{self.historyNames[self.historySelect.currentIndex()]}.txt").is_file():
                with open(self.dataStore / f"history/{self.historyNames[self.historySelect.currentIndex()]}.txt", "r") as file:
                    self.chat_display.clear()
                    text = file.read()
                    split = self.splitText(text)
                    if len(split) >= 2:
                        if split[0].startswith(self.delims["system"]) and self.hiddenDefaultPrompt is not None:
                            if split[1].strip() == self.hiddenDefaultPrompt.strip():
                                self.display_text("".join(split[2:]))
                        else:
                            self.display_text(text)
                    else:
                        self.display_text(text)
            else:
                self.chat_display.clear()
            self.recolour_text()
            self.prevChat = self.historyNames[self.historySelect.currentIndex()]
            self.chat_display.setFocus()
            self.recolour_text()

        except Exception as e:
            self.display_text("loadChat: ", str(e))

    #delete the current chat
    def deleteChat(self):
        try:
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

        except Exception as e:
            self.display_text("deleteChat: ", str(e))

    #create a new chat
    def newChat(self):
        try:
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

            if self.settings.settings["enableSysPrompt"]:
                if not self.settings.settings["hideSysPrompt"]:
                    self.display_text(f"{self.delims["system"]} {self.settings.settings["sysPrompt"]}\n\n")
                else:
                    self.hiddenDefaultPrompt = self.settings.settings["sysPrompt"]
                    #add checks to load chat and stuff for handling to prompt. save hidden like normal
                    #also hide/show if changed default prompt

            self.display_text(f"{self.delims["user"]} ")
            self.recolour_text()
            self.chat_display.setFocus()

        except Exception as e:
            self.display_text("newChat: ", str(e))


    #turn text box into formatted prompt, and generate it
    def prompt(self):
        if self.prompting:
            return
        self.prompting = True
        try:
            prompt = self.chat_display.toPlainText().strip()
            prompt = self.splitText(prompt)

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
                        prompt[counter + 1] = prompt[counter + 1].replace(foundImage[0], "[image]")
                        path = foundImage.group(0).strip('"')
                    else:
                        path = None
                    if path:
                        history.append({"role": role, "content": prompt[counter + 1].strip(), "images": [path]})
                    else:
                        history.append({"role": role, "content": prompt[counter + 1].strip()})


            if self.hiddenDefaultPrompt and not history[0]["role"] == self.delims["system"][:-1]:
                history.insert(0, {"role": "system", "content": self.hiddenDefaultPrompt})
            #threading.Thread(target=self.generateResponse, args=[history], daemon=True).start()
            self.thread = QThread()
            self.worker = PromptWorker(self, history)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.progress.connect(self.chunk)
            self.thread.start()

        except Exception as e:
            self.display_text("prompt: ", str(e))

    def chunk(self, chunk):
        if chunk == "assis12":
            self.display_text(f"\n\n{self.delims["assistant"]} ")
            self.recolour_text()
        elif chunk == "usr12":
            self.display_text(f"\n\n{self.delims["user"]} ")
            self.recolour_text()
        else:
            self.display_text(chunk)

    def generateResponse(self, history):
        try:
            self.settings.settings["prevModel"] = self.model
            self.settings.saveSettingsFile()

            self.display_text(f"\n\n{self.delims["assistant"]} ")
            #self.recolour_text()
            stream = chat(
                model=self.model,
                messages=history,
                stream=True,
            )
            for chunk in stream:
                self.display_text(chunk['message']['content'], end="")
            self.display_text(f"\n\n{self.delims["user"]} ")
            self.recolour_text()
            self.prompting = False

        except Exception as e:
            self.display_text("generateResponse: ", str(e))


    # change the model
    def changeModel(self):
        try:
            self.model = self.modelSelect.currentText()

        except Exception as e:
            self.display_text("changeModel: ", str(e))

    #delete temp folder on end
    def exit_handler(self):
        path = self.dataStore / f"history/temp{os.getpid()}"
        if path.is_dir():
            for child in path.iterdir():
                if child.is_file():
                    child.unlink()
            path.rmdir()

    # recolour all text in text box
    def recolour_text(self):
        try:
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

        except Exception as e:
            self.display_text("recolourText: ", str(e))

    # display text in the text box
    def display_text(self, text, end=""):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text + end)
        self.chat_display.ensureCursorVisible()

    # handle shift-enter and recolour text while talking
    def eventFilter(self, obj, event):
        try:
            if obj is self.chat_display and event.type() == event.KeyPress:
                if event.key() == Qt.Key_Return and event.modifiers() == Qt.ShiftModifier:
                    self.prompt()
                    return True
                elif event.key() == Qt.Key_Space:
                    self.recolour_text()
            return super().eventFilter(obj, event)
        except Exception as e:
            print("eventFilter", str(e))

    def moveEvent(self, event):
        # Restart timer whenever moveEvent fires
        self._move_resize_timer.start(500)
        super().moveEvent(event)

    def resizeEvent(self, event):
        # Restart timer whenever resizeEvent fires
        self._move_resize_timer.start(500)
        super().resizeEvent(event)

    def on_move_resize_finished(self):
        self.moveOrResize.emit("movedOrResized")

if __name__ == "__main__":
    Chat.Main()