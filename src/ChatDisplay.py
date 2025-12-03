import re

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QTextCharFormat, QTextCursor, QColor
from PyQt5.QtWidgets import QHBoxLayout, QWidget, QTextEdit


class ChatDisplay(QWidget):
    autoShowRaw = pyqtSignal()
    autoShowMarkdown = pyqtSignal()
    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)
        self.rawDisplay = self.createRawDisplay()
        layout.addWidget(self.rawDisplay)
        self.markdownDisplay = self.createMarkdownDisplay()
        layout.addWidget(self.markdownDisplay)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)


    #Chat display
    def createRawDisplay(self):
        rawDisplay = QTextEdit()
        rawDisplay.setAcceptRichText(False)
        rawDisplay.setLineWrapMode(QTextEdit.WidgetWidth)
        return rawDisplay
    def createMarkdownDisplay(self):
        markdownDisplay = QTextEdit()
        markdownDisplay.setAcceptRichText(False)
        markdownDisplay.setLineWrapMode(QTextEdit.WidgetWidth)
        markdownDisplay.hide()
        return markdownDisplay

    def setRawVisibility(self, x, delims):
        if x:
            self.rawDisplay.show()
        else:
            """if self.markdownDisplay.isVisible():
                self.rawDisplay.hide()
            else:
                self.autoShowRaw.emit()"""
            self.rawDisplay.hide()
            if not self.markdownDisplay.isVisible():
                self.autoShowMarkdown.emit()
                self.setMarkdownVisibility(True, delims)
    def setMarkdownVisibility(self, x, delims):
        if x:
            self.markdownDisplay.show()
            self.renderMarkdown()
            self.recolour_text(delims)
        else:
            """if self.rawDisplay.isVisible():
                self.markdownDisplay.hide()
            else:
                self.autoShowMarkdown.emit()"""
            self.markdownDisplay.hide()
            if not self.rawDisplay.isVisible():
                self.autoShowRaw.emit()
                self.setRawVisibility(True, delims)


    def renderRaw(self):
        markdown = self.markdownDisplay.toMarkdown()
        #there is a fixed maximum line width so must remove certain \n
        markdown = re.sub(r'(?<!\n)(?<!\|)(?<!-)\n(?!\n)(?!\|)(?!\d)(?!\*)(?!-)', ' ', markdown)
        savedCursor = self.rawDisplay.textCursor()

        self.rawDisplay.blockSignals(True)
        self.rawDisplay.setText(markdown)
        #self.recolourRaw()
        self.rawDisplay.blockSignals(False)

        self.rawDisplay.setTextCursor(savedCursor)

    def renderMarkdown(self):
        if self.markdownDisplay.isVisible():
            text = self.rawDisplay.toPlainText()
            #text = text.split()
            savedCursor = self.markdownDisplay.textCursor()

            self.markdownDisplay.blockSignals(True)
            self.markdownDisplay.setMarkdown(text)
            # self.recolourMarkdown()
            self.markdownDisplay.blockSignals(False)

            self.markdownDisplay.setTextCursor(savedCursor)


    # recolour all text in text box
    def recolour_text(self, delims):
        try:
            def py_to_qt_index(s, py_index):
                # utf-16-le: 2 bytes per code unit; subtract BOM
                return len(s[:py_index].encode("utf-16-le")) // 2
            for obj in [self.rawDisplay, self.markdownDisplay]:
                text = obj.toPlainText()
                cursor = obj.textCursor()
                cursor.select(QTextCursor.Document)
                cursor.mergeCharFormat(QTextCharFormat())

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
                    end = py_to_qt_index(text, match.end()-1)
                    #end = py_to_qt_index(text, matches[i + 1].start()) if i + 1 < len(matches) else len(
                    #    text.encode("utf-16-le")) // 2

                    fmt = QTextCharFormat()
                    fmt.setForeground(role_color)
                    cursor.setPosition(start)
                    cursor.setPosition(end, QTextCursor.KeepAnchor)
                    cursor.mergeCharFormat(fmt)
        except Exception as e:
            import traceback
            self.display_text("recolourText error:\n" + traceback.format_exc())

    # display text in the text box
    def display_text(self, text, end=""):
        #move cursor to end and insert text
        cursor = self.rawDisplay.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text + end)
        self.renderMarkdown()
        self.rawDisplay.ensureCursorVisible()

    #display a chunk of output from the worker
    def chunk(self, chunk, delims):
        if chunk == "assis12":
            if self.rawDisplay.hasFocus():
                self.display_text(f"\n\n")
            self.display_text(f"{delims["assistant"]} ")
            self.recolour_text(delims)
        elif chunk == "usr12":
            self.display_text(f"\n\n{delims["user"]} ")
            self.recolour_text(delims)
        else:
            self.display_text(chunk)

    #clear previous response if the user wants to regenerate
    def deleteForRegen(self, delims):
        #get rid of: empty after user, user, response, assistant
        text = re.split(f"({delims["user"]}|{delims["assistant"]}|{delims["system"]})", self.rawDisplay.toPlainText())[:-4]
        #remove newlines from last remaining item
        text[-1] = text[-1][:-2]
        self.rawDisplay.clear()
        self.display_text("".join(text))

    def getText(self):
        return self.rawDisplay.toPlainText().strip()
    def clearText(self):
        self.rawDisplay.clear()