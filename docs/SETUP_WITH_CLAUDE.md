# Setting up Rovust with Claude

If you use Claude Code (or any coding assistant that can run commands on your
computer), paste the prompt below. It installs everything and starts the
program. If you do not use Claude, use `setup.bat` instead — see the README.

```
Set up and run the Rovust project on this computer:

1. Repository: https://github.com/buggYateer/rovust
   Clone it (or download the main-branch zip if git is missing) into a folder
   named Rovust inside my home directory, unless I say otherwise.
2. Make sure Python 3.12 or newer is available (install it if it is not).
3. Inside the project folder create a virtual environment in .venv, upgrade pip
   and install requirements.txt.
4. Verify with:  python -c "import numpy, scipy, sklearn, matplotlib, PySide6"
   If Windows reports "An Application Control policy has blocked this file",
   tell me to turn off Smart App Control (Windows Security > App & browser
   control) and stop; do not try to work around it.
5. Run the test suite once (pytest) and tell me the result.
6. Start the program with:  python main.py
   and tell me how to start it next time (run.bat or the desktop shortcut).

Do not change any project files.
```
