import re

from PyQt5.Qt import Qt
from PyQt5.QtCore import pyqtSignal, QThreadPool, QThread, QObject

from PromptWorker import PromptWorker


class PromptHandler(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    reGen = pyqtSignal()
    updatePrevModel = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.prompting = False

        self.threadpool = QThreadPool()
        self.thread = QThread()
        self.worker = PromptWorker()
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self.endPrompt, Qt.QueuedConnection)
        self.worker.progress.connect(self.chunk, Qt.QueuedConnection)
        self.worker.reGen.connect(self.deleteForRegen, Qt.QueuedConnection)
        self.thread.start()

    def endPrompt(self):
        self.prompting = False
    def chunk(self, chunk):
        self.progress.emit(f"{chunk}")
    def deleteForRegen(self):
        self.reGen.emit()
    def endGeneration(self):
        self.worker.endGeneration()

    def splitText(self, text, delims):
        try:
            return re.split(f"({delims["user"]}|{delims["assistant"]}|{delims["system"]})", text, flags=re.IGNORECASE)[1:]
        except Exception as e:
            self.progress.emit(f"splitText: {str(e)}")

    #turn text box into formatted prompt, and generate it
    def prompt(self, prompt, delims, model, enableSysPrompt, sysPrompt):
        if self.prompting:
            self.worker.endGeneration()
            return
        self.prompting = True
        try:
            prompt = self.splitText(prompt, delims)
            if len(prompt) < 2:
                self.prompting = False
                return
            if enableSysPrompt:
                self.worker.startPrompt.emit(model, prompt, delims, sysPrompt)
            else:
                self.worker.startPrompt.emit(model, prompt, delims, "")

            self.updatePrevModel.emit(model)
        except Exception as e:
            self.progress.emit("prompt main: ", str(e))