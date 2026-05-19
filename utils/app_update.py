import json
import logging
import re
import urllib.error
import urllib.request

from utils.app_info import get_app_version, get_update_metadata_url

logger = logging.getLogger("AppUpdate")


def parse_version_parts(version):
    """Converts a version string into a comparable tuple of integers."""
    parts = re.findall(r"\d+", version or "")
    if not parts:
        return (0,)
    return tuple(int(part) for part in parts)


def is_newer_version(candidate_version, current_version):
    return parse_version_parts(candidate_version) > parse_version_parts(current_version)


def check_for_updates(timeout=5.0):
    """Fetches a remote update manifest and compares it with the current version."""
    current_version = get_app_version()
    metadata_url = get_update_metadata_url()

    if not metadata_url:
        return {
            "status": "not_configured",
            "current_version": current_version,
            "message": "Nenhuma URL de atualizacao foi configurada.",
        }

    try:
        with urllib.request.urlopen(metadata_url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        logger.warning(f"Falha ao consultar atualizacoes em {metadata_url}: {exc}")
        return {
            "status": "error",
            "current_version": current_version,
            "message": f"Nao foi possivel verificar atualizacoes: {exc}",
            "metadata_url": metadata_url,
        }
    except json.JSONDecodeError as exc:
        logger.warning(f"Manifesto de atualizacao invalido em {metadata_url}: {exc}")
        return {
            "status": "error",
            "current_version": current_version,
            "message": "O manifesto de atualizacao retornado nao e um JSON valido.",
            "metadata_url": metadata_url,
        }

    latest_version = str(payload.get("version", "")).strip()
    download_url = str(payload.get("download_url", "")).strip()
    notes = str(payload.get("notes", "")).strip()

    if not latest_version:
        return {
            "status": "error",
            "current_version": current_version,
            "message": "O manifesto de atualizacao nao informou a versao mais recente.",
            "metadata_url": metadata_url,
        }

    result = {
        "current_version": current_version,
        "latest_version": latest_version,
        "download_url": download_url,
        "notes": notes,
        "metadata_url": metadata_url,
    }

    if is_newer_version(latest_version, current_version):
        result["status"] = "update_available"
        result["message"] = f"Nova versao disponivel: {latest_version}"
    else:
        result["status"] = "up_to_date"
        result["message"] = "Voce ja esta usando a versao mais recente."

    return result
