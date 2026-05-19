import os
import sys

def get_project_root():
    """Returns the root directory of the project."""
    if getattr(sys, 'frozen', False):
        # Running as a compiled PyInstaller executable
        return os.path.dirname(sys.executable)
    else:
        # Running as a Python script inside utils/
        return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

def get_transcripts_dir():
    """Returns the path to the transcriptions directory."""
    path = os.path.join(get_project_root(), "transcricoes")
    os.makedirs(path, exist_ok=True)
    return path

def get_logs_dir():
    """Returns the path to the logs directory."""
    path = os.path.join(get_project_root(), "logs")
    os.makedirs(path, exist_ok=True)
    return path

def get_models_dir():
    """Returns the path to the models directory."""
    path = os.path.join(get_project_root(), "models")
    os.makedirs(path, exist_ok=True)
    return path
