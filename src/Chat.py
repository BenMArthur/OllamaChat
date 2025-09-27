import sys
import re
import threading
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject
from ollama import chat
from ollama import list as ollamaList
from Settings import Settings
from UI import UI
import os
import atexit

class Chat(QObject):

    def __init__(self):
        app = QApplication(sys.argv)
        super().__init__()

        models = [str(model.model) for model in ollamaList().models]
        self.hiddenDefaultPrompt = None
        self.prevChat = None
        self.deletingTemp = False
        self.dataStore = Path.home() / 'AppData/Roaming/OChat'
        self.dataStore.mkdir(parents=True, exist_ok=True)
        atexit.register(self.exit_handler)

        screen = app.primaryScreen().availableGeometry()
        self.settings = Settings(self.dataStore, screen)
        self.settings.submitted.connect(self.fetchSettings)

        if self.settings.settings["loadFixedModel"]:
            self.model = self.settings.settings["selectedModel"]

        elif self.settings.settings["prevModel"] != "":
            self.model = self.settings.settings["prevModel"]
        else:
            self.model = models[0]

        #create UI
        self.UI = UI(self.dataStore, models, self.model,
                     self.settings.settings["pos"], self.settings.settings["size"])
        #connect up UI
        self.UI.historySelect.currentIndexChanged.connect(self.loadChat)
        self.UI.saveButton.clicked.connect(self.saveChat)
        self.UI.deleteButton.clicked.connect(self.deleteChat)
        self.UI.newButton.clicked.connect(self.newChat)
        self.UI.modelSelect.currentIndexChanged.connect(self.changeModel)
        self.UI.settingsButton.clicked.connect(self.settings.toggleSettings)
        self.UI.chat_display.installEventFilter(self.UI)

        #emitters from UI
        self.UI.newPrompt.connect(self.prompt)
        self.UI.moveOrResize.connect(lambda: self.settings.movedOrResized(self.UI.pos(), self.UI.size()))

        self.fetchSettings()

        self.newChat()
        app.exec()


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
            self.UI.delims = self.delims

        except Exception as e:
            self.UI.display_text("fetchSettings: ", str(e))

    #save chat permenantly
    def saveChat(self):
        try:
            currentIndex = self.UI.historySelect.currentIndex()
            newName = self.UI.historyInput.text()
            i=0
            while newName in [self.UI.historyNames[j] for j in range(len(self.UI.historyNames)) if j != currentIndex]:
                i+=1
                if f"{newName}({i})" not in self.UI.historyNames:
                    newName = f"{self.UI.historyInput.text()} ({i})"

            if (self.dataStore / f"history/{self.UI.historyNames[currentIndex]}.txt").is_file():
                Path.rename(self.dataStore / f"history/{self.UI.historyNames[currentIndex]}.txt", self.dataStore / f"history/{newName}.txt")
            else:
                (self.dataStore / "history").mkdir(parents=True, exist_ok=True)
                with open(self.dataStore / f"history/{newName}.txt", "w"):
                    pass

            ToWrite = self.addHiddenPromptIfNeeded(self.UI.chat_display.toPlainText())
            with open(self.dataStore / f"history/{newName}.txt", "w") as file:
                file.write(ToWrite)

            self.UI.historySelect.clear()
            self.UI.historyNames[currentIndex] = newName
            self.UI.historySelect.addItems(self.UI.historyNames)
            self.UI.historyInput.setText(newName)
            self.UI.historySelect.setCurrentIndex(currentIndex)

        except Exception as e:
            self.UI.display_text("saveChat: ", str(e))

    #save chat as a temporary chat when switching away
    def saveTemp(self):
        try:
            (self.dataStore / f"history/temp{os.getpid()}").mkdir(parents=True, exist_ok=True)

            ToWrite = self.addHiddenPromptIfNeeded(self.UI.chat_display.toPlainText())
            with open(self.dataStore / f"history/temp{os.getpid()}/{self.prevChat}.txt", "w") as file:
                file.write(ToWrite)

        except Exception as e:
            self.UI.display_text("saveTemp: ", str(e))

    def splitText(self, text):
        try:
            return re.split(f"({self.delims["user"]}|{self.delims["assistant"]}|{self.delims["system"]})", text, re.IGNORECASE)[1:]
        except Exception as e:
            self.UI.display_text("addHiddenPromptIfNeeded: ", str(e))

    def addHiddenPromptIfNeeded(self, text):
        try:
            split = self.splitText(text)
            if not split[0].startswith(self.delims["system"]) and self.hiddenDefaultPrompt:
                text = f"{self.delims["system"]} {self.hiddenDefaultPrompt}\n\n{text}"
            return text

        except Exception as e:
            self.UI.display_text("addHiddenPromptIfNeeded: ", str(e))

    #load the chat selected in the dropdown
    def loadChat(self):
        try:
            if self.prevChat is not None and not self.deletingTemp:
                self.saveTemp()
            self.deletingTemp = False

            self.UI.historyInput.setText(self.UI.historyNames[self.UI.historySelect.currentIndex()])
            if (self.dataStore / f"history/temp{os.getpid()}/{self.UI.historyNames[self.UI.historySelect.currentIndex()]}.txt").is_file():
                with open(self.dataStore / f"history/temp{os.getpid()}/{self.UI.historyNames[self.UI.historySelect.currentIndex()]}.txt", "r") as file:
                    self.UI.chat_display.clear()
                    text = file.read()
                    split = self.splitText(text)
                    if len(split) >= 2:
                        if split[0].startswith(self.delims["system"]) and split[1].strip() == self.hiddenDefaultPrompt.strip():
                            self.UI.display_text("".join(split[2:]))
                        else:
                            self.UI.display_text(text)
                    else:
                        self.UI.display_text(text)
            elif (self.dataStore / f"history/{self.UI.historyNames[self.UI.historySelect.currentIndex()]}.txt").is_file():
                with open(self.dataStore / f"history/{self.UI.historyNames[self.UI.historySelect.currentIndex()]}.txt", "r") as file:
                    self.UI.chat_display.clear()
                    text = file.read()
                    split = self.splitText(text)
                    if len(split) >= 2:
                        if split[0].startswith(self.delims["system"]) and split[1].strip() == self.hiddenDefaultPrompt.strip():
                            self.UI.display_text("".join(split[2:]))
                        else:
                            self.UI.display_text(text)
                    else:
                        self.UI.display_text(text)
            else:
                self.UI.chat_display.clear()
            self.UI.recolour_text(self.delims)
            self.prevChat = self.UI.historyNames[self.UI.historySelect.currentIndex()]
            self.UI.chat_display.setFocus()

        except Exception as e:
            self.UI.display_text("loadChat: ", str(e))

    #delete the current chat
    def deleteChat(self):
        try:
            nameToDelete = self.UI.historySelect.currentText()

            self.UI.chat_display.clear()
            if (self.dataStore / f"history/{nameToDelete}.txt").is_file():
                (self.dataStore / f"history/{nameToDelete}.txt").unlink()
            if (self.dataStore / f"history/temp{os.getpid()}/{nameToDelete}.txt").is_file():
                self.deletingTemp = True
                (self.dataStore / f"history/temp{os.getpid()}/{nameToDelete}.txt").unlink()

            self.UI.historyNames.remove(nameToDelete)
            if len(self.UI.historyNames) == 0:
                self.newChat()
                pass
            self.UI.historySelect.clear()
            self.UI.historySelect.addItems(self.UI.historyNames)

        except Exception as e:
            self.UI.display_text("deleteChat: ", str(e))

    #create a new chat
    def newChat(self):
        try:
            self.UI.historyNames.insert(0, None)
            default = "new chat 1"
            i = 1
            while default in self.UI.historyNames:
                default = f"{default[:-1]}{str(i)}"
                i += 1
            self.UI.historyNames[0] = default
            self.UI.chat_display.clear()
            self.UI.historySelect.clear()
            self.UI.historySelect.addItems(self.UI.historyNames)

            if self.settings.settings["enableSysPrompt"]:
                if not self.settings.settings["hideSysPrompt"]:
                    self.UI.display_text(f"{self.delims["system"]} {self.settings.settings["sysPrompt"]}\n\n")
                else:
                    self.hiddenDefaultPrompt = self.settings.settings["sysPrompt"]
                    #add checks to load chat and stuff for handling to prompt. save hidden like normal
                    #also hide/show if changed default prompt

            self.UI.display_text(f"{self.delims["user"]} ")
            self.UI.recolour_text(self.delims)
            self.UI.chat_display.setFocus()

        except Exception as e:
            self.UI.display_text("newChat: ", str(e))


    #turn text box into formatted prompt, and generate it
    def prompt(self):
        try:
            prompt = self.UI.chat_display.toPlainText().strip()
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
                        history.append({"role": role, "content": prompt[counter + 1].strip("\n "), "images": [path]})
                    else:
                        history.append({"role": role, "content": prompt[counter + 1].strip("\n ")})


            if self.hiddenDefaultPrompt and not history[0]["role"] == self.delims["system"][:-1]:
                history.insert(0, {"role": "system", "content": self.hiddenDefaultPrompt})

            threading.Thread(target=self.generateResponse, args=[history], daemon=True).start()

        except Exception as e:
            self.UI.display_text("prompt: ", str(e))

    #generate and display a prompt given a history
    def generateResponse(self, history):
        try:
            self.settings.settings["prevModel"] = self.model
            self.settings.saveSettingsFile()

            self.UI.display_text(f"\n\n{self.delims["assistant"]} ")
            self.UI.recolour_text(self.delims)
            stream = chat(
                model=self.model,
                messages=history,
                stream=True,
            )
            for chunk in stream:
                self.UI.display_text(chunk['message']['content'], end="")
            self.UI.display_text(f"\n\n{self.delims["user"]} ")
            self.UI.recolour_text(self.delims)

        except Exception as e:
            self.UI.display_text("toggleSettings: ", str(e))

    # change the model
    def changeModel(self):
        try:
            self.model = self.UI.modelSelect.currentText()

        except Exception as e:
            self.UI.display_text("changeModel: ", str(e))

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