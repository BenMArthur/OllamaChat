from PyQt5.QtCore import QObject, pyqtSignal
from ollama import chat
import re
from pathlib import Path


class PromptWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    reGen = pyqtSignal(str)

    def __init__(self, chat, splitPrompt, delims, hiddenDefaultPrompt):
        super().__init__()
        self.chat = chat
        self.splitPrompt = splitPrompt
        self.delims = delims
        self.hiddenDefaultPrompt = hiddenDefaultPrompt

    def prompt(self):
        try:
            history = []
            missingImages = False
            for counter in range(0, len(self.splitPrompt), 2):
                if counter + 1 < len(self.splitPrompt):
                    role = None
                    if self.splitPrompt[counter].lower().startswith(self.delims["user"]):
                        role = "user"
                    elif self.splitPrompt[counter].lower().startswith(self.delims["assistant"]):
                        role = "assistant"
                    elif self.splitPrompt[counter].lower().startswith(self.delims["system"]):
                        role = "system"

                    images = re.findall(r"[A-za-z]:[\\/][^:]+.(?:png|jpg|jpeg|webp)", self.splitPrompt[counter + 1], flags=re.IGNORECASE)
                    if len(images)>0:
                        for pair in [(image, Path(image).is_file()) for image in images]:
                            if not pair[1]:
                                missingImages = True
                                self.progress.emit(f"\nimage not found - {pair[0]}")

                    if counter + 1 == len(self.splitPrompt) - 1 and self.splitPrompt[-1] == "":
                        history = history[:-1]
                        self.reGen.emit("regen")
                    else:
                        if len(images) > 0:
                            history.append({"role": role, "content": self.splitPrompt[counter + 1].strip(), "images": images})
                        else:
                            history.append({"role": role, "content": self.splitPrompt[counter + 1].strip()})

            if missingImages:
                self.chat.prompting = False
                self.finished.emit()
                return

            if self.hiddenDefaultPrompt and not history[0]["role"] == self.delims["system"][:-1]:
                history.insert(0, {"role": "system", "content": self.hiddenDefaultPrompt})
            self.generateResponse(history)
        except Exception as e:
            self.chat.ui.chat_display("prompt worker: ", str(e))

    def generateResponse(self, history):
        try:
            self.chat.settings.settings["prevModel"] = self.chat.model
            self.chat.settings.saveSettingsFile()

            self.progress.emit("assis12")
            stream = chat(
                model=self.chat.model,
                messages=history,
                stream=True,
            )
            for chunk in stream:
                self.progress.emit(chunk['message']['content'])
            self.progress.emit("usr12")
            self.chat.prompting = False

        except Exception as e:
            self.chat.display_text("toggleSettings: ", str(e))
        self.finished.emit()