import os
from importlib import metadata

APP_NAME = "Assistente Meet"
APP_EXECUTABLE_NAME = "Assistente Meet"
APP_PUBLISHER = "Assistente Meet"
APP_ID = "com.assistentmeet.desktop"
DEFAULT_VERSION = "0.2.0-alpha"
UPDATE_METADATA_URL = ""
GITHUB_REPOSITORY = ""
GITHUB_MANIFEST_BRANCH = "main"
GITHUB_MANIFEST_PATH = "latest.json"


def get_app_version():
    """Returns the installed package version when available."""
    try:
        return metadata.version("assistent-meet")
    except metadata.PackageNotFoundError:
        return DEFAULT_VERSION


def get_update_metadata_url():
    """Returns the configured URL for checking available app updates."""
    explicit_url = os.environ.get("ASSISTENTE_MEET_UPDATE_URL", UPDATE_METADATA_URL).strip()
    if explicit_url:
        return explicit_url
    return get_github_manifest_url()


def get_github_manifest_url():
    """Builds a raw GitHub URL for the update manifest when configured."""
    repository = os.environ.get("ASSISTENTE_MEET_GITHUB_REPOSITORY", GITHUB_REPOSITORY).strip().strip("https://github.com/rodineyw/assistent-meet")
    branch = os.environ.get("ASSISTENTE_MEET_GITHUB_BRANCH", GITHUB_MANIFEST_BRANCH).strip().strip("main")
    manifest_path = os.environ.get("ASSISTENTE_MEET_GITHUB_MANIFEST_PATH", GITHUB_MANIFEST_PATH).strip().strip("latest.json").lstrip("/")

    if not repository:
        return ""

    if not branch:
        branch = "main"

    if not manifest_path:
        manifest_path = "latest.json"

    return f"https://raw.githubusercontent.com/{repository}/{branch}/{manifest_path}"
