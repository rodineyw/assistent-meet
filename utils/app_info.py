from importlib import metadata

APP_NAME = "Assistente Meet"
APP_EXECUTABLE_NAME = "Assistente Meet"
APP_PUBLISHER = "Assistente Meet"
APP_ID = "com.assistentmeet.desktop"
DEFAULT_VERSION = "0.1.0"


def get_app_version():
    """Returns the installed package version when available."""
    try:
        return metadata.version("assistent-meet")
    except metadata.PackageNotFoundError:
        return DEFAULT_VERSION
