import re

from PyQt5.QtGui import QTextCharFormat, QTextCursor, QColor
from PyQt5.QtWidgets import QHBoxLayout, QWidget, QTextEdit


class ChatDisplay(QWidget):
    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)
        layout.addWidget(self.createChatDisplay())
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)


    #Chat display
    def createChatDisplay(self):
        self.chat_display = QTextEdit()
        self.chat_display.setAcceptRichText(False)
        self.chat_display.setLineWrapMode(QTextEdit.WidgetWidth)

        return self.chat_display


    # recolour all text in text box
    def recolour_text(self, delims):
        try:
            def py_to_qt_index(s, py_index):
                # utf-16-le: 2 bytes per code unit; subtract BOM
                return len(s[:py_index].encode("utf-16-le")) // 2

            text = self.chat_display.toPlainText()
            cursor = self.chat_display.textCursor()
            cursor.select(QTextCursor.Document)
            cursor.setCharFormat(QTextCharFormat())

            pattern = re.compile(f"({delims['user']}|{delims['assistant']}|{delims['system']})",
                                 re.IGNORECASE)
            matches = list(pattern.finditer(text.lower()))

            for i, match in enumerate(matches):
                role_text = match.group().lower()
                if delims["user"] in role_text:
                    role_color = QColor("blue")
                elif delims["assistant"] in role_text:
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
            self.display_text("recolourText error:\n" + traceback.format_exc())

    # display text in the text box
    def display_text(self, text, end=""):
        #move cursor to end and insert text
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text + end)
        self.chat_display.ensureCursorVisible()

    #display a chunk of output from the worker
    def chunk(self, chunk, delims):
        if chunk == "assis12":
            self.display_text(f"\n\n{delims["assistant"]} ")
            self.recolour_text(delims)
        elif chunk == "usr12":
            self.display_text(f"\n\n{delims["user"]} ")
            self.recolour_text(delims)
        else:
            self.display_text(chunk)

    #clear previous response if the user wants to regenerate
    def deleteForRegen(self, delims):
        #get rid of: empty after user, user, response, assistant
        text = re.split(f"({delims["user"]}|{delims["assistant"]}|{delims["system"]})", self.chat_display.toPlainText())[:-4]
        #remove newlines from last remaining item
        text[-1] = text[-1][:-2]
        self.chat_display.clear()
        self.display_text("".join(text))