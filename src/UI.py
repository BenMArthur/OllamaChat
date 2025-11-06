import os
import re

from PyQt5.Qt import Qt
from PyQt5.QtCore import pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QTextCharFormat, QTextCursor, QColor, QIcon
from PyQt5.QtWidgets import QMainWindow, QComboBox, QPushButton, QLineEdit, QHBoxLayout, QWidget, QVBoxLayout, QTextEdit

from LoadImage import resource_path


class UI(QMainWindow):
    newPrompt = pyqtSignal(str)
    moveOrResize = pyqtSignal(str)
    def __init__(self, dataStore, models, model, pos, size):
        super().__init__()

        self.dataStore = dataStore
        self.moveResizeTimer = QTimer()
        self.moveResizeTimer.setSingleShot(True)
        self.moveResizeTimer.timeout.connect(self.moveResizeFinished)

        self.delims = {""}

        self.setWindowTitle("Chat")
        self.setWindowIcon(QIcon(resource_path("./img/chat.png")))
        self.resize(size[0], size[1])
        self.move(pos[0], pos[1])

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.addLayout(self.topBar(models, model))
        layout.addWidget(self.createChatDisplay())

        #make it appear on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.show()
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    #Top bar
    def topBar(self, models, model):
        topLayout = QHBoxLayout()

        #left aligned
        #history dropdown
        self.historySelect = QComboBox(editable=True)
        self.historySelect.setFixedWidth(18)
        self.historySelect.view().setMinimumWidth(146)
        self.historyNames = [path.name[:-4] for path in list(sorted((self.dataStore / f"history").glob('*.txt')))]
        topLayout.addWidget(self.historySelect)
        #history text box
        self.historyInput = QLineEdit()
        self.historyInput.setFixedWidth(125)
        topLayout.addWidget(self.historyInput)

        self.saveButton = QPushButton(text="💾")
        self.saveButton.setFixedWidth(27)
        topLayout.addWidget(self.saveButton)

        self.deleteButton = QPushButton(text="❌")
        self.deleteButton.setFixedWidth(27)
        topLayout.addWidget(self.deleteButton)

        self.newButton = QPushButton(text="📖")
        self.newButton.setFixedWidth(27)
        topLayout.addWidget(self.newButton)

        # right aligned
        topLayout.addStretch(1)

        self.modelSelect = QComboBox()
        self.modelSelect.setFixedWidth(180)
        self.modelSelect.addItems(models)
        self.modelSelect.setCurrentText(model)
        topLayout.addWidget(self.modelSelect)

        self.settingsButton = QPushButton(text="⚙")
        self.settingsButton.setFixedWidth(27)
        topLayout.addWidget(self.settingsButton)

        return(topLayout)

    #Chat display
    def createChatDisplay(self):
        self.chat_display = QTextEdit()
        self.chat_display.setAcceptRichText(False)
        self.chat_display.setLineWrapMode(QTextEdit.WidgetWidth)

        return self.chat_display


    # recolour all text in text box
    def recolour_text(self):
        try:
            def py_to_qt_index(s, py_index):
                # utf-16-le: 2 bytes per code unit; subtract BOM
                return len(s[:py_index].encode("utf-16-le")) // 2

            text = self.chat_display.toPlainText()
            cursor = self.chat_display.textCursor()
            cursor.select(QTextCursor.Document)
            cursor.setCharFormat(QTextCharFormat())

            pattern = re.compile(f"({self.delims['user']}|{self.delims['assistant']}|{self.delims['system']})",
                                 re.IGNORECASE)
            matches = list(pattern.finditer(text.lower()))

            for i, match in enumerate(matches):
                role_text = match.group().lower()
                if self.delims["user"] in role_text:
                    role_color = QColor("blue")
                elif self.delims["assistant"] in role_text:
                    role_color = QColor("green")
                else:
                    role_color = QColor("gray")

                start = py_to_qt_index(text, match.start())
                end = py_to_qt_index(text, matches[i + 1].start()) if i + 1 < len(matches) else len(
                    text.encode("utf-16-le")) // 2

                fmt = QTextCharFormat()
                fmt.setForeground(role_color)
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.KeepAnchor)
                cursor.setCharFormat(fmt)
        except Exception as e:
            import traceback
            print(self.delims)
            self.display_text("recolourText error:\n" + traceback.format_exc())

    # display text in the text box
    def display_text(self, text, end=""):
        #move cursor to end and insert text
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text + end)
        self.chat_display.ensureCursorVisible()

    #display a chunk of output from the worker
    def chunk(self, chunk):
        if chunk == "assis12":
            self.display_text(f"\n\n{self.delims["assistant"]} ")
            self.recolour_text()
        elif chunk == "usr12":
            self.display_text(f"\n\n{self.delims["user"]} ")
            self.recolour_text()
        else:
            self.display_text(chunk)

    #clear previous response if the user wants to regenerate
    def deleteForRegen(self):
        #get rid of: empty after user, user, response, assistant
        text = re.split(f"({self.delims["user"]}|{self.delims["assistant"]}|{self.delims["system"]})", self.chat_display.toPlainText())[:-4]
        #remove newlines from last remaining item
        text[-1] = text[-1][:-2]
        self.chat_display.clear()
        self.display_text("".join(text))

    # handle shift-enter and recolour text while typing
    def eventFilter(self, obj, event):
        try:
            if obj is not self.chat_display:
                return False

            if event.type() != QEvent.KeyPress:
                return False

            key = event.key()

            if key == Qt.Key_Return and event.modifiers() == Qt.ShiftModifier:
                self.newPrompt.emit(self.chat_display.toPlainText().strip())
                return True

            if key == Qt.Key_Space:
                self.recolour_text()
                return super().eventFilter(obj, event)

            return False
        except Exception as e:
            self.display_text(f"eventFilter: {str(e)}")

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
        path = self.dataStore / f"history/temp{os.getpid()}"
        if path.is_dir():
            for child in path.iterdir():
                if child.is_file():
                    child.unlink()
            path.rmdir()
        super().closeEvent(event)