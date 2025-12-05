import re
import time
import os
from pathlib import Path
from xmlrpc.client import Boolean

from PyQt5.QtCore import pyqtSignal, QObject


class ChatHandler(QObject):
    display = pyqtSignal(str)
    recolour = pyqtSignal()
    clear = pyqtSignal()
    updateChatNames = pyqtSignal(list, str, Boolean)
    endGeneration = pyqtSignal()
    changeCurrentChatName = pyqtSignal(str)

    def __init__(self, datastore, prevChat):
        super().__init__()

        self.prevChat = None
        self.deletingTemp = False
        self.dataStore = datastore
        self.dataStore.mkdir(parents=True, exist_ok=True)

        self.prevChat = prevChat

    #save chat permenantly
    def saveChat(self, currentIndex, newName, allNames, fullChat, enableSysPrompt, sysPrompt, delims):
        try:
            i=0
            if newName.strip() == "" or any([x in newName for x in [":","\\"]]):
                newName = "default name"
            while newName in [allNames[j] for j in range(len(allNames)) if j != currentIndex]:
                i+=1
                if f"{newName} ({i})" not in allNames:
                    newName = f"{newName} ({i})"

            if (self.dataStore / f"history/{allNames[currentIndex]}.txt").is_file():
                Path.rename(self.dataStore / f"history/{allNames[currentIndex]}.txt", self.dataStore / f"history/{newName}.txt")
            else:
                (self.dataStore / "history").mkdir(parents=True, exist_ok=True)
                with open(self.dataStore / f"history/{newName}.txt", "w"):
                    pass
            toWrite = self.addHiddenPromptIfNeeded(fullChat, enableSysPrompt, sysPrompt, delims)
            with open(self.dataStore / f"history/{newName}.txt", "w", encoding="utf-8") as file:
                file.write(toWrite)

            self.saveTemp(fullChat, enableSysPrompt, sysPrompt, delims)
            allNames[currentIndex] = newName

            self.updateChatNames.emit(allNames, newName, False)


        except Exception as e:
            self.display.emit(f"saveChat: {str(e)}")

    #save chat as a temporary chat when switching away
    def saveTemp(self, fullChat, enableSysPrompt, sysPrompt, delims):
        try:
            if self.prevChat is None:
                return
            (self.dataStore / f"history/temp{os.getpid()}").mkdir(parents=True, exist_ok=True)
            toWrite = self.addHiddenPromptIfNeeded(fullChat, enableSysPrompt, sysPrompt, delims)
            with open(self.dataStore / f"history/temp{os.getpid()}/{self.prevChat}.txt", "w", encoding="utf-8") as file:
                file.write(toWrite)

        except Exception as e:
            self.display.emit(f"saveTemp: {str(e)}")

    def addHiddenPromptIfNeeded(self, text, enableSysPrompt, sysPrompt, delims):
        try:
            if text:
                split = self.splitText(text, delims)
                if len(split)>0:
                    if not split[0].startswith(delims["system"]) and sysPrompt.strip() != "" and enableSysPrompt:
                        text = f"{delims["system"]} {sysPrompt}\n\n{text}"
                return text
            return ""
        except Exception as e:
            self.display.emit(f"addHiddenPromptIfNeeded: {str(e)}")

    def splitText(self, text, delims):
        try:
            return re.split(f"({delims["user"]}|{delims["assistant"]}|{delims["system"]})", text, flags=re.IGNORECASE)[1:]
        except Exception as e:
            self.display.emit(f"splitText: {str(e)}")

    #load the chat selected in the dropdown
    def loadChat(self, prompting, fullChat, deletingTemp, allNames, currentIndex, loadPerm, enableSysPrompt, hideSysPrompt, sysPrompt, delims):
        try:
            if prompting:
                self.endGeneration.emit()
                time.sleep(0.001)
            if self.prevChat is not None and not deletingTemp:
                self.saveTemp(fullChat, enableSysPrompt, sysPrompt, delims)
            self.deletingTemp = False

            self.changeCurrentChatName.emit(allNames[currentIndex])

            paths = [(self.dataStore / f"history/temp{os.getpid()}/{allNames[currentIndex]}.txt"), (self.dataStore / f"history/{allNames[currentIndex]}.txt")]
            for i in range(len(paths)):
                if i == 0 and loadPerm:
                    continue
                if paths[i].is_file():
                    with open(paths[i], "r", encoding="utf-8") as file:
                        self.clear.emit()
                        text = file.read()
                        split = self.splitText(text, delims)
                        if len(split) >= 2:
                            if split[0].startswith(delims["system"]) and sysPrompt.strip() != "":
                                if split[
                                    1].strip() == sysPrompt.strip() and enableSysPrompt and hideSysPrompt:
                                    self.display.emit("".join(split[2:]))
                                else:
                                    self.display.emit(text)
                            else:
                                self.display.emit(text)
                        else:
                            self.display.emit(text)
                    #stop if temp has been loaded
                    break
            self.prevChat = allNames[currentIndex]
            #self.chatDisplay.rawDisplay.setFocus()
            self.recolour.emit()

        except Exception as e:
            self.display.emit(f"loadChat: {str(e)}")

    #delete the current chat
    def deleteChat(self, prompting, allNames, nameToDelete, fullText, sysPrompt, enableSysPrompt, hideSysPrompt, delims):
        try:
            if prompting:
                self.endGeneration()
            self.clear.emit()
            if (self.dataStore / f"history/{nameToDelete}.txt").is_file():
                (self.dataStore / f"history/{nameToDelete}.txt").unlink()
            if (self.dataStore / f"history/temp{os.getpid()}/{nameToDelete}.txt").is_file():
                self.deletingTemp = True
                (self.dataStore / f"history/temp{os.getpid()}/{nameToDelete}.txt").unlink()
            index = allNames.index(nameToDelete)
            allNames.remove(nameToDelete)
            if len(allNames) == 0:
                self.newChat(prompting, fullText, sysPrompt, allNames, True, enableSysPrompt, hideSysPrompt, delims)
            if index == len(allNames):
                newName = allNames[index-1]
            else:
                newName = allNames[index]
            self.updateChatNames.emit(allNames, "", False)

        except Exception as e:
            self.display.emit(f"deleteChat: {str(e)}")

    #create a new chat
    def newChat(self, prompting, fullText, sysPrompt, allNames, save, enableSysPrompt, hideSysPrompt, delims):
        try:
            if prompting:
                self.endGeneration.emit()
            if save:
                self.saveTemp(fullText, enableSysPrompt, sysPrompt, delims)
            allNames.insert(0, None)
            default = "new chat"
            i = 0

            while default in allNames:
                i += 1
                if f"{default} {i}" not in allNames:
                    default = f"{default} {i}"

            allNames[0] = default
            self.clear.emit()
            self.updateChatNames.emit(allNames, default, True)
            if enableSysPrompt:
                if not hideSysPrompt:
                    self.display.emit(f"{delims["system"]} {sysPrompt}\n\n")

            self.display.emit(f"{delims["user"]} ")
            self.recolour.emit()
            self.prevChat = default

        except Exception as e:
            self.display.emit(f"newChat: {str(e)}")

    def clearTemp(self):
        temp_dir = self.dataStore / f"history/temp{os.getpid()}"
        if temp_dir.is_dir():
            for item in temp_dir.iterdir():
                if item.is_file() or item.is_symlink():
                    item.unlink()
        allNames = sorted([path.name[:-4] for path in list(sorted((self.dataStore / f"history").glob('*.txt')))])
        self.updateChatNames.emit(allNames, "", False)
        #self.topBar.historySelect.clear()
        #self.topBar.historySelect.addItems(self.topBar.historyNames)