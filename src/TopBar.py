from PyQt5.QtWidgets import QComboBox, QPushButton, QLineEdit, QHBoxLayout, QWidget, QCheckBox


class TopBar(QWidget):
    def __init__(self, dataStore):
        super().__init__()

        self.dataStore = dataStore
        buttonWidth = 25

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        """left aligned"""
        # history dropdown
        self.historySelect = QComboBox(editable=True)
        self.historySelect.setMaximumWidth(18)
        self.historySelect.view().setMinimumWidth(143)
        self.historyNames = [path.name[:-4] for path in list(sorted((self.dataStore / f"history").glob('*.txt')))]
        layout.addWidget(self.historySelect)
        # history text box
        self.historyInput = QLineEdit()
        self.historyInput.setMaximumWidth(125)
        self.historyInput.setMinimumWidth(80)
        layout.addWidget(self.historyInput)

        self.saveButton = self.makeButton("💾", buttonWidth)
        layout.addWidget(self.saveButton)

        self.revertButton = self.makeButton("🔄", buttonWidth)
        layout.addWidget(self.revertButton)

        self.deleteButton = self.makeButton("❌", buttonWidth)
        layout.addWidget(self.deleteButton)

        self.newButton = self.makeButton("📖", buttonWidth)
        layout.addWidget(self.newButton)

        """right aligned"""
        layout.addStretch(1)

        self.checkboxRaw = QCheckBox("Raw ")
        self.checkboxRaw.setChecked(True)
        self.checkboxMarkdown = QCheckBox("Markdown ")

        style = """
            QCheckBox {
                background-color: #FFFFFFFF;
                border: 1px solid #AAAAAAAA;
                border-radius: 3px;
                padding: 2px 1px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox:hover {
                background-color: #dcebfc;
                border: 1px solid #4a90e2;
            }
            """
        self.checkboxRaw.setStyleSheet(style)
        self.checkboxMarkdown.setStyleSheet(style)

        layout.addWidget(self.checkboxRaw)
        layout.addWidget(self.checkboxMarkdown)

        self.modelSelect = QComboBox()
        self.modelSelect.setMaximumWidth(180)
        self.modelSelect.setMinimumWidth(80)
        layout.addWidget(self.modelSelect)

        self.settingsButton = self.makeButton("⚙", buttonWidth)
        layout.addWidget(self.settingsButton)

    def makeButton(self, text, size):
        button = QPushButton(text)
        button.setMaximumWidth(size)
        button.setMaximumHeight(size)
        return button

    def updateModels(self, models, model):
        self.modelSelect.clear()
        self.modelSelect.addItems(models)
        self.modelSelect.setCurrentText(model)

    def newChatNames(self, allNames, newName, blockSignals):
        allNames = sorted(allNames)
        self.historyNames = allNames

        if blockSignals:
            self.historySelect.blockSignals(True)

        self.historySelect.clear()
        self.historySelect.addItems(allNames)
        if newName != "":
            self.historySelect.setCurrentIndex(allNames.index(newName))
            self.historyInput.setText(newName)

        if blockSignals:
            self.historySelect.blockSignals(False)