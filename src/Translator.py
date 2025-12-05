import re
import markdown
import html2text


class BaseTranslator:
    """Abstract base class for translators."""
    def rawToRich(self, richDisplay, rawDisplay):
        raise NotImplementedError("Subclasses must implement rawToRich")

    def richToRaw(self, delims, richDisplay, rawDisplay):
        raise NotImplementedError("Subclasses must implement richToRaw")


class HTMLTranslator(BaseTranslator):
    """Translator for HTML content."""
    def rawToRich(self, richDisplay, rawDisplay):
        if richDisplay.isVisible():
            text = rawDisplay.toPlainText()
            savedCursor = richDisplay.textCursor()

            # Convert Markdown delimiters to HTML
            html = markdown.markdown(text, extensions = ["codehilite",
                                                         "fenced_code",
                                                         "footnotes",
                                                         "sane_lists",
                                                         "smarty",
                                                         "tables",
                                                         "wikilinks"
                                                    ])
            html = f"""
            <html>
            <head>
            <style>
            table, th, td {{
                border: 1px solid black;
                border-collapse: collapse;
                padding: 4px;
            }}
            </style>
            </head>
            <body>
            {html}
            </body>
            </html>
            """

            #html = markdown.markdown(text)

            richDisplay.blockSignals(True)
            richDisplay.setHtml(html)
            richDisplay.blockSignals(False)

            richDisplay.setTextCursor(savedCursor)

    def richToRaw(self, delims, richDisplay, rawDisplay):
        # Get HTML from rich display

        html = richDisplay.toHtml()
        savedCursor = rawDisplay.textCursor()

        # Convert HTML back to Markdown delimiters
        h2t = html2text.HTML2Text()
        h2t.body_width = 0   # prevent line wrapping

        # Configure delimiter style
        h2t.emphasis_mark = "*"  # use * instead of _
        h2t.strong_mark = "**"  # use ** instead of __
        richText = h2t.handle(html)

        """
        
        richText = richDisplay.toMarkdown()
        # there is a fixed maximum line width so must remove certain \n
        richText = re.sub(fr'(?<!\n)(?<!\|)(?<!-)(?<!:)\n(?!\n)(?!\t)(?!\|)(?! )(?!\d)(?!\*)(?!-)(?!{delims["assistant"]})', ' ',
                      richText)
        richText = re.sub(r'```(\w+)\s', r'```\1\n', richText)
        richText = re.sub(r' ```', r'\n``` ', richText)
        savedCursor = rawDisplay.textCursor()"""

        rawDisplay.blockSignals(True)
        rawDisplay.setText(richText)
        # self.recolourRaw()
        rawDisplay.blockSignals(False)

        rawDisplay.setTextCursor(savedCursor)



class MarkdownTranslator(BaseTranslator):
    """Translator for Markdown content."""
    def rawToRich(self, richDisplay, rawDisplay):
        if richDisplay.isVisible():
            text = rawDisplay.toPlainText()
            text = re.sub(r': ```', ': \n```', text)
            # text = text.split()
            savedCursor = richDisplay.textCursor()

            richDisplay.blockSignals(True)
            richDisplay.setMarkdown(text)
            # self.recolourMarkdown()
            richDisplay.blockSignals(False)

            richDisplay.setTextCursor(savedCursor)

    def richToRaw(self, delims, richDisplay, rawDisplay):
        # Example: strip Markdown bold markers
        rich = richDisplay.toMarkdown()
        # there is a fixed maximum line width so must remove certain \n
        rich = re.sub(fr'(?<!\n)(?<!\|)(?<!-)(?<!:)\n(?!\n)(?!\t)(?!\|)(?!\d)(?!\*)(?!-)(?!{delims["assistant"]})', ' ',
                      rich)
        rich = re.sub(r'```(\w+)\s', r'```\1\n', rich)
        rich = re.sub(r' ```', r'\n``` ', rich)
        savedCursor = rawDisplay.textCursor()

        rawDisplay.blockSignals(True)
        rawDisplay.setText(rich)
        # self.recolourRaw()
        rawDisplay.blockSignals(False)

        rawDisplay.setTextCursor(savedCursor)

class CustomTranslator(BaseTranslator):
    """Translator for Markdown content."""
    def rawToRich(self, richDisplay, rawDisplay):
        if richDisplay.isVisible():
            text = rawDisplay.toPlainText()
            text = re.sub(r': ```', ': \n```', text)
            # text = text.split()
            savedCursor = richDisplay.textCursor()

            richDisplay.blockSignals(True)
            richDisplay.setMarkdown(text)
            # self.recolourMarkdown()
            richDisplay.blockSignals(False)

            richDisplay.setTextCursor(savedCursor)

    def richToRaw(self, delims, richDisplay, rawDisplay):
        # Example: strip Markdown bold markers
        rich = richDisplay.toMarkdown()
        # there is a fixed maximum line width so must remove certain \n
        rich = re.sub(fr'(?<!\n)(?<!\|)(?<!-)(?<!:)\n(?!\n)(?!\t)(?!\|)(?!\d)(?!\*)(?!-)(?!{delims["assistant"]})', ' ',
                      rich)
        rich = re.sub(r'```(\w+)\s', r'```\1\n', rich)
        rich = re.sub(r' ```', r'\n``` ', rich)
        savedCursor = rawDisplay.textCursor()

        rawDisplay.blockSignals(True)
        rawDisplay.setText(rich)
        # self.recolourRaw()
        rawDisplay.blockSignals(False)

        rawDisplay.setTextCursor(savedCursor)

def makeTranslator(type_: str) -> BaseTranslator:
    """Factory function to create a translator object."""
    type_lower = type_.lower()
    if type_lower == "html":
        return HTMLTranslator()
    elif type_lower == "markdown":
        return MarkdownTranslator()
    elif type_lower == "custom":
        return CustomTranslator()
    else:
        raise ValueError(f"Unknown translator type: {type_}")

"""```markdown
* Level 1
  * Level 2
    * Level 3
```
**How it will look when rendered:**

*   Level 1
    *   Level 2
      *   Level 3
"""





"""`* Level 1`

`  * Level 2`

`    * Level 3`

 

**How it will look when rendered:**

- Level 1
  - Level 2
  - Level 3

"""