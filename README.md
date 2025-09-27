An app for interacting with your ollama models \
You must install [ollama](ollama.com) and download a model 

alt+space will open the window, shift+return will submit a prompt \
all prompts, responses, and system prompts are stored in an editbale text box, so it is easy regenerate responses or edit/streamline them to not have unneeded information that would distract the model

all chats are temporarily saved until you delete them or close the window \
to save chats between sessions you must press the save button  
updates to chats will also be saved temporarily, but to lock in those updates you must press the save button again.


\
You can download the .exe from here, or you can get the src files, install all the dependencies in a venv, and build it yourself using: pyinstaller --onefile --noconsole --name OChat src/runChat.py

Put the exe somewhere and run it once, it will then run on startup \
to completely uninstall it, delete the exe, /appdata/roaming/OChat, and /AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/OChat.lnk

only works for windows, probably wouldnt be hard to change it for another platform