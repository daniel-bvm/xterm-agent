find . | grep -E "(/__pycache__$|\.pyc$|\.pyo$)" | xargs rm -rf
rm -rf xterm.zip
zip -r xterm.zip Dockerfile requirements.txt system_prompt.txt terminal_controller.py config.json