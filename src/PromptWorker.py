from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt
from ollama import chat
import re
from pathlib import Path


class PromptWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    reGen = pyqtSignal(str)

    startPrompt = pyqtSignal(object, object, object, object)

    def __init__(self):
        super().__init__()
        self.stopGeneration = False
        self.startPrompt.connect(self.prompt, Qt.QueuedConnection)

    @pyqtSlot(object, object, object, object)
    def prompt(self, model, splitPrompt, delims, hiddenDefaultPrompt):
        try:
            if len(splitPrompt)==2:
                if splitPrompt[1] == "":
                    self.finished.emit()
                    return
            self.stopGeneration = False
            history = []
            missingImages = False

            for counter in range(0, len(splitPrompt), 2):
                if counter + 1 < len(splitPrompt):
                    role = None
                    if splitPrompt[counter].lower().startswith(delims["user"]):
                        role = "user"
                    elif splitPrompt[counter].lower().startswith(delims["assistant"]):
                        role = "assistant"
                    elif splitPrompt[counter].lower().startswith(delims["system"]):
                        role = "system"

                    images = re.findall(r"[A-Za-z]:[\\/][^:]+.(?:png|jpg|jpeg|webp)", splitPrompt[counter + 1], flags=re.IGNORECASE)
                    if len(images)>0:
                        for pair in [(image, Path(image).is_file()) for image in images]:
                            if not pair[1]:
                                missingImages = True
                                self.progress.emit(f"\nimage not found - {pair[0]}")

                    if counter + 1 == len(splitPrompt) - 1 and splitPrompt[-1] == "" and len(splitPrompt)>=4:
                        if splitPrompt[-4] == delims["assistant"]:
                            history = history[:-1]
                            self.reGen.emit("regen")
                    else:
                        if len(images) > 0:
                            history.append({"role": role, "content": splitPrompt[counter + 1].strip(), "images": images})
                        else:
                            history.append({"role": role, "content": splitPrompt[counter + 1].strip()})

            if missingImages:
                self.finished.emit()
                return

            if hiddenDefaultPrompt and not history[0]["role"] == delims["system"][:-1]:
                history.insert(0, {"role": "system", "content": hiddenDefaultPrompt})
            self.generateResponse(history, model)
        except Exception as e:
            print("prompt worker: ", str(e))
            import traceback
            print("prompt worker: An error occurred")
            traceback.print_exc()

    def generateResponse(self, history, model):
        try:
            self.progress.emit("assis12")
            stream = chat(
                model=model,
                messages=history,
                stream=True,
            )
            for chunk in stream:
                if self.stopGeneration:
                    stream.close()
                    break
                self.progress.emit(chunk['message']['content'])

            if self.stopGeneration:
                self.stopGeneration = False
            self.progress.emit("usr12")

        except Exception as e:
            self.progress.emit(f"gen response: {str(e)}")
        self.finished.emit()

    def endGeneration(self):
        self.stopGeneration = True