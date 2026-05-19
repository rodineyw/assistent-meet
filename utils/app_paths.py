import os
import sys

APP_DATA_DIRNAME = "Assistente Meet"


def is_frozen():
    """Returns True when running from a bundled executable."""
    return getattr(sys, "frozen", False)


def get_source_root():
    """Returns the repository root when running from source."""
    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def get_resource_root():
    """Returns the directory that contains bundled application resources."""
    if is_frozen():
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return get_source_root()


def get_project_root():
    """Returns the writable root for app data."""
    if is_frozen():
        local_appdata = os.environ.get("LOCALAPPDATA")
        if not local_appdata:
            local_appdata = os.path.join(os.path.expanduser("~"), "AppData", "Local")
        path = os.path.join(local_appdata, APP_DATA_DIRNAME)
        os.makedirs(path, exist_ok=True)
        return path
    return get_source_root()


def get_ui_asset_path(filename):
    """Returns the absolute path to a file inside the UI assets directory."""
    return os.path.join(get_resource_root(), "ui", filename)


def get_app_icon_path():
    """Returns the preferred icon asset path when available."""
    for filename in ("icone.svg", "icon.svg", "icone.ico", "icon.ico"):
        path = get_ui_asset_path(filename)
        if os.path.exists(path):
            return path
    return None

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
