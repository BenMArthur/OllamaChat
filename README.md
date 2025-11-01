# Ollama Chat
An app for interacting with your ollama models

## Requirements
You must install [ollama](ollama.com) and download a model. \
ollama must run on startup

## Usage
- **Open window:** `Alt + Space`  
- **Submit prompt** `Shift + Enter with a prompt after user:`
- **regenerate response** `Shift + Enter with nothing after user:`
- **stop generation** `Shift + Enter while generating:`

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
- edits will also be saved temporarily, but to lock in those edits you must press the save button again.


## Instalation
### Downloading
1. You can download the .exe from the realeases here
2. or you can clone the src files, install all the dependencies in a venv, and build it yourself using:
```pyinstaller --onefile --add-data=./src/img/:./img/ --noconsole -i ./src/img/icon.ico --name OllamaChat src/runChat.py```

### Installing
Put the exe somewhere and run it once \
it will then run on startup

### Uninstalation
to fully delete 
1. delete the exe
2. delete /appdata/roaming/ollamaChat
3. delete /AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/OllamaChat.lnk

only works for windows, probably wouldnt be hard to change it for another platform