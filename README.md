# Ollama Chat
An app for interacting with your ollama models

## Requirements
You must install [ollama](ollama.com) and download a model. \
ollama must run on startup

## Usage
- **Open/close window:** `Ctrl + Alt + Space`  
- **Submit prompt** `Shift + Enter` with a prompt after user:
- **regenerate response** `Shift + Enter` with nothing after user:
- **stop generation** `Shift + Enter` while generating:
- **intervening in generation** `Shift + Enter` with no user: will treat the content after assistant: as the start of the generated response. 
  - Doesn't really work with thinking models i.e. deepseek
  - I haven't looked too much into it, or with different thinking models, however, by default thoughts are not displayed, this seem to treat the tokens generated so far (the start of the content) as the start of the thoughts, it will then generate thoughts at normal, but generate them as content. Content then is generated as normal
- A lot of things from the same command, but they make sense once you try it out.

all prompts, responses, and system prompts are stored in an editbale text box, so it is easy to regenerate responses or edit/streamline them to not have unneeded information that would distract the model

## Images
Should work with any number of images in your prompt.\
This is the format used:
```python
 re.findall(r"[A-za-z]:[\\/][^:]+.(?:png|jpg|jpeg|webp)", <prompt item>, flags=re.IGNORECASE)
```

## Saving Chats
- all chats are temporarily saved until you delete them or close the window
- to save chats between sessions you must press the save button 
- edits will be saved temporarily as you switch between chats, but closing the window will delete all temporary saves
- to lock in edits you must press the save button again.
- you can press the arrow button to revert to the permenant save
- all saves are stored in plain text .txt files in /appdata/roaming/ollamaChat/history


## Instalation
### Downloading
1. You can download the .exe from the realeases here
2. or you can clone the src files, install all the dependencies in a venv, and build it yourself using:
```pyinstaller --onefile --add-data=./src/img/:./img/ --noconsole -i ./src/img/icon.ico --name OllamaChat src/runChat.py```

### Installing
Put the exe somewhere and run it once \
it will then run on startup \
if it crashes for some reason you can run it again. But I should have fixed the crashing.

### Uninstalation
to fully delete 
1. delete the exe
2. delete /appdata/roaming/ollamaChat
3. delete /AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/OllamaChat.lnk

only works for windows, probably wouldnt be hard to change it for another platform
