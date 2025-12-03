import re
import os
import sys
from pathlib import Path
from ollama import list as ollamaList

from PyQt5.Qt import Qt
from PyQt5.QtCore import pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication

from Settings import Settings
from LoadImage import resource_path
from TopBar import TopBar
from ChatDisplay import ChatDisplay
from ChatHandler import ChatHandler
from PromptHandler import PromptHandler


class App(QMainWindow):
    toggleSignal = pyqtSignal()

    newPrompt = pyqtSignal()
    moveOrResize = pyqtSignal(str)
    userClosed = pyqtSignal()

    def __init__(self, screen, appName):
        super().__init__()

        self.moveResizeTimer = QTimer()
        self.moveResizeTimer.setSingleShot(True)
        self.moveResizeTimer.timeout.connect(self.moveResizeFinished)


        self.sysPrompt = ""
        self.enableSysPrompt = False
        self.hideSysPrompt = False
        self.delims = None
        self.prevChat = None
        self.deletingTemp = False
        self.prompting = False
        self.appName = appName
        self.dataStore = Path.home() / f"AppData/Roaming/{self.appName}"
        self.dataStore.mkdir(parents=True, exist_ok=True)
        historyPath = self.dataStore / f"history"
        if historyPath.is_dir():
            for tempPath in historyPath.iterdir():
                if tempPath.is_dir() and tempPath.name.startswith("temp"):
                    for tempSavePath in tempPath.iterdir():
                        if tempSavePath.is_file:
                            tempSavePath.unlink()
                    tempPath.rmdir()

        self.settings = Settings(self.dataStore, screen, self.appName)
        self.settings.submitted.connect(self.fetchSettings)

        """
        -----------------------------------------------------------------------
        ------------             create window                -----------------
        -----------------------------------------------------------------------
        """
        self.setWindowTitle("Chat")
        self.setWindowIcon(QIcon(resource_path("./img/chat.png")))
        pos = self.settings.settings["pos"]
        size = self.settings.settings["size"]
        self.resize(size[0], size[1])
        self.move(pos[0], pos[1])

        self.moveOrResize.connect(lambda: self.settings.movedOrResized(self.pos(), self.size()))
        self.userClosed.connect(self.settings.hide)
        self.toggleSignal.connect(self.toggleVisible)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(6, 6, 6, 6)

        """
        -----------------------------------------------------------------------
        ------------                Top Bar                    ----------------
        -----------------------------------------------------------------------
        """
        self.topBar = TopBar(self.dataStore)
        self.prevChat = self.topBar.historyInput.text().lower()
        layout.addWidget(self.topBar)
        self.topBar.historySelect.currentIndexChanged.connect(
            lambda: self.chatHandler.loadChat(
                self.prompting,
                self.chatDisplay.getText(),
                self.deletingTemp,
                self.topBar.historyNames,
                self.topBar.historySelect.currentIndex(),
                False,
                self.enableSysPrompt,
                self.hideSysPrompt,
                self.sysPrompt,
                self.delims
            ))

        self.topBar.saveButton.clicked.connect(
            lambda: self.chatHandler.saveChat(
                self.topBar.historySelect.currentIndex(),
                self.topBar.historyInput.text().lower(),
                self.topBar.historyNames,
                self.chatDisplay.getText(),
                self.enableSysPrompt,
                self.sysPrompt,
                self.delims
            ))
        self.topBar.revertButton.clicked.connect(
            lambda: self.chatHandler.loadChat(
                self.prompting,
                self.chatDisplay.getText(),
                self.deletingTemp,
                self.topBar.historyNames,
                self.topBar.historySelect.currentIndex(),
                True,
                self.enableSysPrompt,
                self.hideSysPrompt,
                self.sysPrompt,
                self.delims
            ))
        self.topBar.deleteButton.clicked.connect(
            lambda: self.chatHandler.deleteChat(
                self.prompting,
                self.topBar.historyNames,
                self.topBar.historySelect.currentText(),
                self.chatDisplay.getText(),
                self.settings.settings["sysPrompt"],
                self.enableSysPrompt,
                self.hideSysPrompt,
                self.delims
            ))
        self.topBar.newButton.clicked.connect(
            lambda: self.chatHandler.newChat(
                self.prompting,
                self.chatDisplay.getText(),
                self.settings.settings["sysPrompt"],
                self.topBar.historyNames,
                True,
                self.enableSysPrompt,
                self.hideSysPrompt,
                self.delims
            ))

        self.topBar.modelSelect.currentIndexChanged.connect(self.changeModel)
        self.topBar.settingsButton.clicked.connect(self.settings.toggleSettings)
        self.topBar.historyInput.installEventFilter(self)

        """
        -----------------------------------------------------------------------
        ------------              Chat Display                 ----------------
        -----------------------------------------------------------------------
        """
        self.chatDisplay = ChatDisplay()
        layout.addWidget(self.chatDisplay)
        self.chatDisplay.rawDisplay.installEventFilter(self)
        self.chatDisplay.markdownDisplay.installEventFilter(self)

        self.chatDisplay.autoShowRaw.connect(lambda: self.topBar.checkboxRaw.setChecked(True))
        self.chatDisplay.autoShowMarkdown.connect(lambda: self.topBar.checkboxMarkdown.setChecked(True))

        self.topBar.checkboxRaw.clicked.connect(lambda x: self.chatDisplay.setRawVisibility(x, self.delims))
        self.topBar.checkboxMarkdown.clicked.connect(lambda x: self.chatDisplay.setMarkdownVisibility(x, self.delims))

        """
        -----------------------------------------------------------------------
        ------------             Prompt Handler                ----------------
        -----------------------------------------------------------------------
        """
        self.promptHandler = PromptHandler()
        self.promptHandler.progress.connect(lambda chunk: self.chatDisplay.chunk(chunk, self.delims), Qt.QueuedConnection)
        self.promptHandler.reGen.connect(lambda: self.chatDisplay.deleteForRegen(self.delims), Qt.QueuedConnection)
        self.promptHandler.updatePrevModel.connect(self.settings.updatePrevModel)

        self.newPrompt.connect(
            lambda: self.promptHandler.prompt(
                self.chatDisplay.getText(),
                self.delims,
                self.model,
                self.enableSysPrompt,
                self.sysPrompt
            ))

        """
        -----------------------------------------------------------------------
        ------------              Chat Handler                 ----------------
        -----------------------------------------------------------------------
        """
        self.chatHandler = ChatHandler(self.dataStore, self.topBar.historyInput.text().lower())
        self.chatHandler.display.connect(self.chatDisplay.display_text)
        self.chatHandler.recolour.connect(lambda: self.chatDisplay.recolour_text(self.delims))
        self.chatHandler.clear.connect(self.chatDisplay.clearText)
        self.chatHandler.endGeneration.connect(self.promptHandler.endGeneration)
        self.chatHandler.changeCurrentChatName.connect(self.topBar.historyInput.setText)
        self.chatHandler.updateChatNames.connect(self.topBar.newChatNames)

        """
        -----------------------------------------------------------------------
        ------------           Initialise Settings             ----------------
        -----------------------------------------------------------------------
        """
        self.fetchSettings()


    def toggleVisible(self):
        if self.isHidden():
            self.updateModels()
            self.chatHandler.newChat(self.prompting,
                                     self.chatDisplay.getText(),
                                     self.settings.settings["sysPrompt"],
                                     self.topBar.historyNames,
                                     False,
                                     self.enableSysPrompt,
                                     self.hideSysPrompt,
                                     self.delims
            )
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.show()
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.show()
        else:
            self.chatDisplay.clearText()
            self.chatHandler.clearTemp()
            self.hide()
            self.settings.hide()

    def updateModels(self):
        models = sorted([str(model.model) for model in ollamaList().models])
        if self.settings.settings["loadFixedModel"] and self.settings.settings["selectedModel"] in models:
            self.model = self.settings.settings["selectedModel"]
        elif self.settings.settings["prevModel"] != "" and self.settings.settings["prevModel"] in models:
            self.model = self.settings.settings["prevModel"]
        else:
            self.model = models[0]

        self.topBar.updateModels(models, self.model)
        self.settings.updateModels(models)

    #get settings when they are changed
    def fetchSettings(self):
        try:
            newDelims = {"user": f"{self.settings.settings["delimUser"]}:",
                           "assistant": f"{self.settings.settings["delimAssistant"]}:",
                           "system": f"{self.settings.settings["delimSystem"]}:"}
            if self.delims is None:
                self.delims = newDelims
            else:
                self.changeDelims(newDelims)

            text = self.chatDisplay.getText()
            self.enableSysPrompt, self.hideSysPrompt, self.sysPrompt, newText = self.settings.fetchSysPromptSettings(text, self.enableSysPrompt, self.hideSysPrompt, self.sysPrompt)
            if newText != text:
                self.chatDisplay.clearText()
                self.chatDisplay.display_text(newText)
                self.chatDisplay.recolour_text(self.delims)

        except Exception as e:
            self.chatDisplay.display_text("fetchSettings: ", str(e))

    def changeDelims(self, newDelims):
        try:
            changes = []
            for key in newDelims.keys():
                if newDelims[key] != self.delims[key]:
                    changes.append([self.delims[key], newDelims[key]])
            if len(changes) == 0:
                return

            currentText = self.chatDisplay.getText()
            for i in range(len(changes)):
                currentText = currentText.replace(changes[i][0], changes[i][1])

            self.chatDisplay.clearText()
            self.chatDisplay.display_text(currentText)
            self.delims = newDelims
            self.chatDisplay.recolour_text(self.delims)

            permSaves = self.dataStore / f"history/"
            tempSaves = self.dataStore / f"history/temp{os.getpid()}"
            for directory in [permSaves, tempSaves]:
                if directory.is_dir():
                    for path in directory.iterdir():
                        if path.is_file():
                            with open(path, "r", encoding="utf-8") as file:
                                text = file.read()
                            for change in changes:
                                text = text.replace(change[0], change[1])
                            with open(path, "w", encoding="utf-8") as file:
                                file.write(text)

        except Exception as e:
            self.chatDisplay.display_text("changeDelims: ", str(e))

    def splitText(self, text):
        try:
            return re.split(f"({self.delims["user"]}|{self.delims["assistant"]}|{self.delims["system"]})", text, flags=re.IGNORECASE)[1:]
        except Exception as e:
            self.display.emit(f"splitText: {str(e)}")

    # change the model
    def changeModel(self):
        try:
            self.model = self.topBar.modelSelect.currentText()
        except Exception as e:
            self.chatDisplay.display_text("changeModel: ", str(e))

    # handle shift-enter and recolour text while typing
    def eventFilter(self, obj, event):
        try:
            if event.type() != QEvent.KeyPress:
                return False

            key = event.key()
            if obj is self.chatDisplay.rawDisplay or obj is self.chatDisplay.markdownDisplay:

                if (key == Qt.Key_Return or key == Qt.Key_Enter) and event.modifiers() == Qt.ShiftModifier:
                    if obj is self.chatDisplay.rawDisplay:
                        self.chatDisplay.renderMarkdown()
                    else:
                        self.chatDisplay.renderRaw()
                    self.newPrompt.emit()
                    return True

                if key == Qt.Key_Space:
                    if obj is self.chatDisplay.rawDisplay:
                        self.chatDisplay.renderMarkdown()
                    else:
                        self.chatDisplay.renderRaw()

                    self.chatDisplay.recolour_text(self.delims)
                    return super().eventFilter(obj, event)

            elif obj is self.topBar.historyInput and (key == Qt.Key_Return or key == Qt.Key_Enter):
                name = self.topBar.historyInput.text().lower()
                for i in range(self.historySelect.count()):
                    if self.topBar.historySelect.itemText(i).lower() == name:
                        self.topBar.historySelect.setCurrentIndex(i)
                        return True
            return False
        except Exception as e:
            self.chatDisplay.display_text(f"eventFilter: {str(e)}")

    #save position and size when window has been still for 0.3 seconds
    def moveEvent(self, event):
        self.moveResizeTimer.start(300)
        super().moveEvent(event)
    def resizeEvent(self, event):
        # Restart timer whenever resizeEvent fires
        self.moveResizeTimer.start(300)
        super().resizeEvent(event)
    def moveResizeFinished(self):
        #data = list([self.pos().x(), self.pos().y(), self.size().width(), self.size().height()])
        #self.moveOrResize.emit(data)
        self.moveOrResize.emit("moved")
    #delete temp files
    def closeEvent(self, event):
        app = QApplication.instance()
        userClose = (
                event.type() == QEvent.Close
                and event.spontaneous()  # emitted due to user action
                and not app.isSavingSession()  # not a system shutdown
        )

        if userClose:
            event.ignore()
            self.hide()
            self.userClosed.emit()
            return

        path = self.dataStore / f"history/temp{os.getpid()}"
        if path.is_dir():
            for child in path.iterdir():
                if child.is_file():
                    child.unlink()
            path.rmdir()
        super().closeEvent(event)

if __name__ == "__main__":
    appName = "ollamaChat"
    app = QApplication(sys.argv)
    font = QFont("Arial", 11)
    app.setFont(font)
    chat = App(app.primaryScreen().availableGeometry(), appName)
    chat.toggleSignal.emit()
    app.exec()