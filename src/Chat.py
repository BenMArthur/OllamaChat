import sys
import re
from pathlib import Path
import os
import atexit

from ollama import chat
from ollama import list as ollamaList

from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QObject, QThreadPool, pyqtSignal, QThread

from Settings import Settings
from UI import UI
from PromptWorker import PromptWorker

class Chat(QMainWindow):

    @staticmethod
    def Main(appName):
        app = QApplication(sys.argv)
        Chat(app.primaryScreen().availableGeometry(), appName)
        app.exec()

    newPrompt = pyqtSignal(str)
    moveOrResize = pyqtSignal(str)
    def __init__(self, screen, appName):
        super().__init__()
        self.threadpool = QThreadPool()

        models = [str(model.model) for model in ollamaList().models]
        self.hiddenDefaultPrompt = None
        self.prevChat = None
        self.deletingTemp = False
        self.prompting = False
        self.appName = appName
        self.dataStore = Path.home() / f"AppData/Roaming/{self.appName}"
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


        self.ui = UI(self.dataStore, models, self.model, self.settings.settings["pos"], self.settings.settings["size"])
        #connect up UI
        self.ui.historySelect.currentIndexChanged.connect(self.loadChat)
        self.ui.saveButton.clicked.connect(self.saveChat)
        self.ui.deleteButton.clicked.connect(self.deleteChat)
        self.ui.newButton.clicked.connect(self.newChat)
        self.ui.modelSelect.currentIndexChanged.connect(self.changeModel)
        self.ui.settingsButton.clicked.connect(self.settings.toggleSettings)
        self.ui.chat_display.installEventFilter(self.ui)

        #emitters from UI
        self.ui.newPrompt.connect(self.prompt)
        self.ui.moveOrResize.connect(lambda: self.settings.movedOrResized(self.ui.pos(), self.ui.size()))

        self.fetchSettings()

        self.newChat()


    #get settings when they are changed
    def fetchSettings(self):
        """settings = {"enableSysPrompt": self.enableSysPrompt.isChecked(),
                    "hideSysPrompt": self.hideSysPrompt.isChecked(), "sysPrompt": self.sysPromptInput.toPlainText(),
                    "loadFixedModel": self.defaultModelRadioFixed.isChecked(),
                    "selectedModel": self.modelSelect.currentText()}"""
        try:
            self.delims= {"user": f"{self.settings.settings["delimUser"]}:",
                           "assistant": f"{self.settings.settings["delimAssistant"]}:",
                           "system": f"{self.settings.settings["delimSystem"]}:"}
            self.ui.delims = self.delims

        except Exception as e:
            self.ui.display_text("fetchSettings: ", str(e))

    #save chat permenantly
    def saveChat(self):
        try:
            currentIndex = self.ui.historySelect.currentIndex()
            newName = self.ui.historyInput.text()
            i=0
            while newName in [self.ui.historyNames[j] for j in range(len(self.ui.historyNames)) if j != currentIndex]:
                i+=1
                if f"{newName}({i})" not in self.ui.historyNames:
                    newName = f"{self.ui.historyInput.text()} ({i})"

            if (self.dataStore / f"history/{self.ui.historyNames[currentIndex]}.txt").is_file():
                Path.rename(self.dataStore / f"history/{self.ui.historyNames[currentIndex]}.txt", self.dataStore / f"history/{newName}.txt")
            else:
                (self.dataStore / "history").mkdir(parents=True, exist_ok=True)
                with open(self.dataStore / f"history/{newName}.txt", "w"):
                    pass

            ToWrite = self.addHiddenPromptIfNeeded(self.ui.chat_display.toPlainText())
            with open(self.dataStore / f"history/{newName}.txt", "w") as file:
                file.write(ToWrite)

            self.ui.historySelect.clear()
            self.ui.historyNames[currentIndex] = newName
            self.ui.historySelect.addItems(self.ui.historyNames)
            self.ui.historyInput.setText(newName)
            self.ui.historySelect.setCurrentIndex(currentIndex)

            self.saveTemp()

        except Exception as e:
            self.ui.display_text("saveChat: ", str(e))

    #save chat as a temporary chat when switching away
    def saveTemp(self):
        try:
            (self.dataStore / f"history/temp{os.getpid()}").mkdir(parents=True, exist_ok=True)

            ToWrite = self.addHiddenPromptIfNeeded(self.ui.chat_display.toPlainText())
            with open(self.dataStore / f"history/temp{os.getpid()}/{self.prevChat}.txt", "w") as file:
                file.write(ToWrite)

        except Exception as e:
            self.ui.display_text("saveTemp: ", str(e))

    def splitText(self, text):
        try:
            return re.split(f"({self.delims["user"]}|{self.delims["assistant"]}|{self.delims["system"]})", text, flags=re.IGNORECASE)[1:]
        except Exception as e:
            self.ui.display_text("splitText: ", str(e))

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
            self.ui.display_text("addHiddenPromptIfNeeded: ", str(e))

    #load the chat selected in the dropdown
    def loadChat(self):
        try:
            if self.prevChat is not None and not self.deletingTemp:
                self.saveTemp()
            self.deletingTemp = False

            self.ui.historyInput.setText(self.ui.historyNames[self.ui.historySelect.currentIndex()])
            if (self.dataStore / f"history/temp{os.getpid()}/{self.ui.historyNames[self.ui.historySelect.currentIndex()]}.txt").is_file():
                with open(self.dataStore / f"history/temp{os.getpid()}/{self.ui.historyNames[self.ui.historySelect.currentIndex()]}.txt", "r") as file:
                    self.ui.chat_display.clear()
                    text = file.read()
                    split = self.splitText(text)
                    if len(split) >= 2:
                        if split[0].startswith(self.delims["system"]) and self.hiddenDefaultPrompt is not None:
                            if split[1].strip() == self.hiddenDefaultPrompt.strip():
                                self.ui.display_text("".join(split[2:]))
                        else:
                            self.ui.display_text(text)
                    else:
                        self.ui.display_text(text)
            elif (self.dataStore / f"history/{self.ui.historyNames[self.ui.historySelect.currentIndex()]}.txt").is_file():
                with open(self.dataStore / f"history/{self.ui.historyNames[self.ui.historySelect.currentIndex()]}.txt", "r") as file:
                    self.ui.chat_display.clear()
                    text = file.read()
                    split = self.splitText(text)
                    if len(split) >= 2:
                        if split[0].startswith(self.delims["system"]) and self.hiddenDefaultPrompt is not None:
                            if split[1].strip() == self.hiddenDefaultPrompt.strip():
                                self.ui.display_text("".join(split[2:]))
                        else:
                            self.ui.display_text(text)
                    else:
                        self.ui.display_text(text)
            else:
                self.ui.chat_display.clear()
            self.ui.recolour_text()
            self.prevChat = self.ui.historyNames[self.ui.historySelect.currentIndex()]
            self.ui.chat_display.setFocus()
            self.ui.recolour_text()

        except Exception as e:
            self.ui.display_text("loadChat: ", str(e))

    #delete the current chat
    def deleteChat(self):
        try:
            nameToDelete = self.ui.historySelect.currentText()

            self.ui.chat_display.clear()
            if (self.dataStore / f"history/{nameToDelete}.txt").is_file():
                (self.dataStore / f"history/{nameToDelete}.txt").unlink()
            if (self.dataStore / f"history/temp{os.getpid()}/{nameToDelete}.txt").is_file():
                self.deletingTemp = True
                (self.dataStore / f"history/temp{os.getpid()}/{nameToDelete}.txt").unlink()

            self.ui.historyNames.remove(nameToDelete)
            if len(self.ui.historyNames) == 0:
                self.newChat()
                pass
            self.ui.historySelect.clear()
            self.ui.historySelect.addItems(self.ui.historyNames)

        except Exception as e:
            self.ui.display_text("deleteChat: ", str(e))

    #create a new chat
    def newChat(self):
        try:
            self.ui.historyNames.insert(0, None)
            default = "new chat 1"
            i = 1
            while default in self.ui.historyNames:
                default = f"{default[:-1]}{str(i)}"
                i += 1
            self.ui.historyNames[0] = default
            self.ui.chat_display.clear()
            self.ui.historySelect.clear()
            self.ui.historySelect.addItems(self.ui.historyNames)

            if self.settings.settings["enableSysPrompt"]:
                if not self.settings.settings["hideSysPrompt"]:
                    self.ui.display_text(f"{self.delims["system"]} {self.settings.settings["sysPrompt"]}\n\n")
                else:
                    self.hiddenDefaultPrompt = self.settings.settings["sysPrompt"]
                    #add checks to load chat and stuff for handling to prompt. save hidden like normal
                    #also hide/show if changed default prompt

            self.ui.display_text(f"{self.delims["user"]} ")
            self.ui.recolour_text()
            self.ui.chat_display.setFocus()

        except Exception as e:
            self.ui.display_text("newChat: ", str(e))


    #turn text box into formatted prompt, and generate it
    def prompt(self):
        if self.prompting:
            return
        self.prompting = True
        try:
            prompt = self.ui.chat_display.toPlainText().strip()
            prompt = self.splitText(prompt)
            if len(prompt) < 2:
                return
            self.thread = QThread()
            self.worker = PromptWorker(self, prompt, self.delims, self.hiddenDefaultPrompt)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.prompt)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.progress.connect(self.ui.chunk)
            self.worker.reGen.connect(self.ui.deleteForRegen)
            self.thread.start()
        except Exception as e:
            self.ui.display_text("prompt main: ", str(e))

    # change the model
    def changeModel(self):
        try:
            self.model = self.ui.modelSelect.currentText()
        except Exception as e:
            self.ui.display_text("changeModel: ", str(e))

    #delete temp folder on end
    def exit_handler(self):
        path = self.dataStore / f"history/temp{os.getpid()}"
        if path.is_dir():
            for child in path.iterdir():
                if child.is_file():
                    child.unlink()
            path.rmdir()


if __name__ == "__main__":
    Chat.Main()