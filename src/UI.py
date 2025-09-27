import re
import sys

from PyQt5.Qt import Qt
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QTextCharFormat, QTextCursor, QColor
from PyQt5.QtWidgets import QMainWindow, QComboBox, QPushButton, QLineEdit, QHBoxLayout, QWidget, QVBoxLayout, QTextEdit


class UI(QMainWindow):
    newPrompt = pyqtSignal(str)
    def __init__(self, dataStore, models, model):
        super().__init__()

        self.dataStore = dataStore

        self.setWindowTitle("Chat")
        self.resize(600, 400)
        self.setFocus()
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.topBar(layout, models, model)
        self.createChatDisplay(layout)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.show()
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    # Top bar
    def topBar(self, layout, models, model):
        top_layout = QHBoxLayout()

        # left aligned
        self.historySelect = QComboBox(editable=True)
        self.historySelect.setFixedWidth(18)
        self.historySelect.view().setMinimumWidth(146)
        self.historyNames = [path.name[:-4] for path in list(sorted((self.dataStore / f"history").glob('*.txt')))]
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

        self.delims = [""]

    # Chat display
    def createChatDisplay(self, layout):
        self.chat_display = QTextEdit()
        self.chat_display.setAcceptRichText(False)
        self.chat_display.setLineWrapMode(QTextEdit.WidgetWidth)
        layout.addWidget(self.chat_display)

    # recolour all text in text box
    def recolour_text(self, delims):
        try:
            text = self.chat_display.toPlainText().lower()
            cursor = self.chat_display.textCursor()
            cursor.select(QTextCursor.Document)
            cursor.setCharFormat(QTextCharFormat())  # reset formatting

            pattern = re.compile(f"({delims["user"]}|{delims["assistant"]}|{delims["system"]})")
            matches = list(pattern.finditer(text))

            for i, match in enumerate(matches):
                role_text = match.group().lower()
                role_color = None
                if delims["user"] in role_text:
                    role_color = QColor("blue")
                elif delims["assistant"] in role_text:
                    role_color = QColor("green")
                elif delims["system"] in role_text:
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
                    self.newPrompt.emit("Prompt submitted")
                    return True
                elif event.key() == Qt.Key_Space:
                    self.recolour_text(self.delims)
            return super().eventFilter(obj, event)
        except Exception as e:
            print("eventFilter", str(e))

